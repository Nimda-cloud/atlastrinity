"""Tour Driver for Automated Virtual Navigation
Manages the "physical" movement of the agent through the virtual world (Street View).
"""

import asyncio
import math
import time
from typing import Any

from ..logger import logger
from ..map_state import map_state_manager
from ..mcp_manager import mcp_manager


class TourDriver:
    """Controls the automated navigation loop."""

    def __init__(self):
        self.is_active = False
        self.is_paused = False
        self.current_route_points: list[tuple[float, float]] = []  # [(lat, lng)]
        self.current_step_index = 0
        self.speed_modifier = 1.0  # 0.5 = slow, 2.0 = fast
        self.base_step_duration = 2.0  # seconds between frames
        self.heading_offset = 0  # relative look direction (0 = forward, 90 = right)
        self._task: asyncio.Task | None = None

    async def start_tour(self, route_polyline: str) -> None:
        """Start a tour along a polyline."""
        if self.is_active:
            await self.stop_tour()

        logger.info("[TourDriver] Starting tour...")
        self.current_route_points = self._decode_polyline(route_polyline)

        if not self.current_route_points:
            logger.error("[TourDriver] Failed to decode polyline or empty route.")
            return

        self.is_active = True
        self.is_paused = False
        self.current_step_index = 0
        self.heading_offset = 0

        # Start the async drive loop
        self._task = asyncio.create_task(self._drive_loop())

    async def stop_tour(self) -> None:
        """Stop the tour completely."""
        self.is_active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[TourDriver] Tour stopped.")

    def pause_tour(self) -> None:
        self.is_paused = True
        logger.info("[TourDriver] Tour paused.")

    def resume_tour(self) -> None:
        self.is_paused = False
        logger.info("[TourDriver] Tour resumed.")

    def look_around(self, angle: int) -> None:
        """Change relative viewing angle (e.g., -90 for left)."""
        self.heading_offset = angle
        # Trigger immediate update if paused
        if self.is_paused:
            asyncio.create_task(self._update_view_at_current_location())

    def set_speed(self, modifier: float) -> None:
        """Set speed modifier (0.5 to 3.0)."""
        self.speed_modifier = max(0.5, min(modifier, 3.0))

    async def _drive_loop(self) -> None:
        """Main navigation loop."""
        try:
            while self.is_active and self.current_step_index < len(self.current_route_points):
                if self.is_paused:
                    await asyncio.sleep(0.5)
                    continue

                await self._update_view_at_current_location()

                # Calculate variable sleep based on speed
                sleep_time = self.base_step_duration / self.speed_modifier
                await asyncio.sleep(sleep_time)

                self.current_step_index += 1
            
            logger.info("[TourDriver] Reached destination.")
            self.is_active = False

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"[TourDriver] Error in drive loop: {e}")
            self.is_active = False

    async def _update_view_at_current_location(self) -> None:
        """Fetch and update the view for the current location."""
        if self.current_step_index >= len(self.current_route_points):
            return

        lat, lng = self.current_route_points[self.current_step_index]
        
        # Calculate heading to next point (if available)
        next_lat, next_lng = lat, lng
        if self.current_step_index + 1 < len(self.current_route_points):
             next_lat, next_lng = self.current_route_points[self.current_step_index + 1]
        
        # Determine base navigation heading
        base_heading = self._calculate_bearing(lat, lng, next_lat, next_lng)
        
        # Apply user look offset
        final_heading = (base_heading + self.heading_offset) % 360
        
        # Call Google Maps MCP to get the image (and save it)
        # We assume the MCP tool saves the file and returns the path/info
        try:
            # We use the mcp_manager to call the tool directly
            # Note: We need to format the location string
            location_str = f"{lat},{lng}"
            
            # This calling convention depends on how mcp_manager exposes tools internally
            # For now, we'll assume we can use call_tool from the googlemaps server
            result = await mcp_manager.call_tool(
                "googlemaps", 
                "maps_street_view", 
                {
                    "location": location_str,
                    "heading": int(final_heading),
                    "pitch": 0,
                    "fov": 90,
                    "cyberpunk": True
                }
            )
            
            # Parse result to find the file path
            # The MCP tool returns a text string like "Saved to: /path/to/file.png"
            output_text = result.content[0].text if result.content else ""
            import re
            match = re.search(r"Saved to: (.+)", output_text)
            if match:
                image_path = match.group(1).strip()
                # Update MapState
                map_state_manager.set_agent_view(
                    image_path=image_path,
                    heading=int(final_heading),
                    pitch=0,
                    fov=90
                )
            
        except Exception as e:
            logger.error(f"[TourDriver] Failed to fetch Street View: {e}")

    def _decode_polyline(self, polyline_str: str) -> list[tuple[float, float]]:
        """Decodes a Google Maps encoded polyline string."""
        points = []
        index = 0
        lat = 0
        lng = 0
        length = len(polyline_str)

        while index < length:
            b = 0
            shift = 0
            result = 0
            
            while True:
                b = ord(polyline_str[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            dlat = ~(result >> 1) if (result & 1) else (result >> 1)
            lat += dlat

            shift = 0
            result = 0
            
            while True:
                b = ord(polyline_str[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            dlng = ~(result >> 1) if (result & 1) else (result >> 1)
            lng += dlng

            points.append((lat * 1e-5, lng * 1e-5))

        return points

    def _calculate_bearing(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate bearing between two GPS points."""
        # If points are identical, keep previous heading or default to 0
        if lat1 == lat2 and lng1 == lng2:
            return 0.0

        y = math.sin(math.radians(lng2 - lng1)) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
            math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.cos(math.radians(lng2 - lng1))
        
        bearing = math.atan2(y, x)
        return (math.degrees(bearing) + 360) % 360


# Global instance
tour_driver = TourDriver()
