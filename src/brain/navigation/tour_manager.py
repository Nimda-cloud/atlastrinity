from typing import Any

from src.brain.navigation.tour_driver import tour_driver


class TourMixin:
    """Mixin to handle guided tour logic for the Trinity orchestrator."""

    async def start_tour(self, polyline: str):
        """Start a guided tour along a polyline."""
        await tour_driver.start_tour(polyline)
        return "Tour started."

    async def stop_tour(self):
        """Stop the current tour."""
        await tour_driver.stop_tour()
        return "Tour stopped."

    async def pause_tour(self):
        """Pause the tour."""
        tour_driver.pause_tour()
        return "Tour paused."

    async def resume_tour(self):
        """Resume the tour."""
        tour_driver.resume_tour()
        return "Tour resumed."

    async def look_around(self, angle: int):
        """Change view angle."""
        tour_driver.look_around(angle)
        return f"Looking at angle {angle}."

    async def set_tour_speed(self, modifier: float):
        """Set tour speed."""
        tour_driver.set_speed(modifier)
        return f"Speed set to {modifier}x."
