# Google Maps MCP Server (Swift)

Native Model Context Protocol (MCP) server for Google Maps integration with local Cyberpunk image processing.

## Tools

### Visual Monitoring
- `maps_street_view`: Get a Street View image with optional Cyberpunk styling.
- `maps_static_map`: Generate a static map image with optional Cyberpunk styling.

### Navigation & Traffic
- `maps_directions`: Get turn-by-turn directions with live traffic awareness (`departure_time=now`).
- `maps_distance_matrix`: Calculate travel distance and time with live traffic awareness.

### Location Services
- `maps_geocode`: Convert an address to geographic coordinates.
- `maps_reverse_geocode`: Convert coordinates to a human-readable address.
- `maps_search_places`: Search for places, businesses, and points of interest.
- `maps_place_details`: Get detailed information about a specific place.

### Environmental Data
- `maps_elevation`: Get elevation data for specified locations.

## Configuration

Required environment variables:
- `GOOGLE_MAPS_API_KEY`: Your Google Maps Platform API key.

## Implementation Details
- **Language**: Swift 6.0
- **Image Processing**: Apple Core Image (CyberpunkFilter)
- **SDK**: `modelcontextprotocol/swift-sdk`
