import AppKit
import CoreGraphics
import CoreImage
import Foundation
import MCP

// MARK: - Configuration

let GOOGLE_MAPS_API_KEY = ProcessInfo.processInfo.environment["GOOGLE_MAPS_API_KEY"] ?? ""

// MARK: - Cyberpunk Image Filter

struct CyberpunkFilter {
    // AtlasTrinity Design Colors
    static let atlasBlue = NSColor(red: 0.0, green: 0.64, blue: 1.0, alpha: 1.0)  // #00a3ff
    static let userTurquoise = NSColor(red: 0.0, green: 0.90, blue: 1.0, alpha: 1.0)  // #00e5ff

    /// Apply Cyberpunk filter: blue/cyan color transform + edge detection + glow
    static func apply(to imageData: Data) -> Data? {
        guard let nsImage = NSImage(data: imageData),
              let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil)
        else {
            return imageData
        }

        let ciImage = CIImage(cgImage: cgImage)
        let context = CIContext(options: nil)

        // Step 1: Convert to grayscale and darken
        guard let grayscaleFilter = CIFilter(name: "CIColorControls") else { return imageData }
        grayscaleFilter.setValue(ciImage, forKey: kCIInputImageKey)
        grayscaleFilter.setValue(0.0, forKey: kCIInputSaturationKey)  // Grayscale
        grayscaleFilter.setValue(-0.3, forKey: kCIInputBrightnessKey)  // Darken
        grayscaleFilter.setValue(1.2, forKey: kCIInputContrastKey)  // Increase contrast

        guard let grayImage = grayscaleFilter.outputImage else { return imageData }

        // Step 2: Apply blue/cyan color tint
        guard let colorMatrix = CIFilter(name: "CIColorMatrix") else { return imageData }
        colorMatrix.setValue(grayImage, forKey: kCIInputImageKey)
        // Transform grays to blue-cyan spectrum
        colorMatrix.setValue(CIVector(x: 0, y: 0, z: 0, w: 0), forKey: "inputRVector")  // No red
        colorMatrix.setValue(CIVector(x: 0.4, y: 0.4, z: 0, w: 0), forKey: "inputGVector")  // Some green
        colorMatrix.setValue(CIVector(x: 0.8, y: 0.8, z: 1.0, w: 0), forKey: "inputBVector")  // Strong blue
        colorMatrix.setValue(CIVector(x: 0, y: 0, z: 0, w: 1), forKey: "inputAVector")

        guard let tintedImage = colorMatrix.outputImage else { return imageData }

        // Step 3: Edge detection for contours
        guard let edgeFilter = CIFilter(name: "CIEdges") else { return imageData }
        edgeFilter.setValue(ciImage, forKey: kCIInputImageKey)
        edgeFilter.setValue(2.0, forKey: kCIInputIntensityKey)

        guard let edgesImage = edgeFilter.outputImage else { return imageData }

        // Step 4: Colorize edges to cyan
        guard let edgeColorMatrix = CIFilter(name: "CIColorMatrix") else { return imageData }
        edgeColorMatrix.setValue(edgesImage, forKey: kCIInputImageKey)
        edgeColorMatrix.setValue(CIVector(x: 0, y: 0, z: 0, w: 0), forKey: "inputRVector")
        edgeColorMatrix.setValue(CIVector(x: 0, y: 0.9, z: 0, w: 0), forKey: "inputGVector")
        edgeColorMatrix.setValue(CIVector(x: 0, y: 1.0, z: 1.0, w: 0), forKey: "inputBVector")
        edgeColorMatrix.setValue(CIVector(x: 0, y: 0, z: 0, w: 1), forKey: "inputAVector")

        guard let cyanEdges = edgeColorMatrix.outputImage else { return imageData }

        // Step 5: Blend tinted image with cyan edges (screen blend)
        guard let blendFilter = CIFilter(name: "CIScreenBlendMode") else { return imageData }
        blendFilter.setValue(tintedImage, forKey: kCIInputBackgroundImageKey)
        blendFilter.setValue(cyanEdges, forKey: kCIInputImageKey)

        guard let blendedImage = blendFilter.outputImage else { return imageData }

        // Step 6: Add subtle glow (bloom effect)
        guard let bloomFilter = CIFilter(name: "CIBloom") else { return imageData }
        bloomFilter.setValue(blendedImage, forKey: kCIInputImageKey)
        bloomFilter.setValue(2.0, forKey: kCIInputRadiusKey)
        bloomFilter.setValue(0.5, forKey: kCIInputIntensityKey)

        guard let finalImage = bloomFilter.outputImage else { return imageData }

        // Render to CGImage
        guard let outputCGImage = context.createCGImage(finalImage, from: finalImage.extent) else {
            return imageData
        }

        // Convert to PNG data
        let bitmapRep = NSBitmapImageRep(cgImage: outputCGImage)
        return bitmapRep.representation(using: .png, properties: [:])
    }
}

// MARK: - Google Maps API Helpers

func fetchGoogleMapsAPI(endpoint: String, params: [String: String]) async throws -> Data {
    var components = URLComponents(string: "https://maps.googleapis.com/maps/api/\(endpoint)")!
    var queryItems = params.map { URLQueryItem(name: $0.key, value: $0.value) }
    queryItems.append(URLQueryItem(name: "key", value: GOOGLE_MAPS_API_KEY))
    components.queryItems = queryItems

    guard let url = components.url else {
        throw MCPError.invalidParams("Invalid URL")
    }

    let (data, response) = try await URLSession.shared.data(from: url)

    guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
        throw MCPError.internalError("Google Maps API error")
    }

    return data
}

func fetchJSON(endpoint: String, params: [String: String]) async throws -> [String: Any] {
    let data = try await fetchGoogleMapsAPI(endpoint: endpoint, params: params)
    guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        throw MCPError.internalError("Invalid JSON response")
    }
    return json
}

// MARK: - Tool Implementations

func geocode(address: String) async throws -> String {
    let json = try await fetchJSON(endpoint: "geocode/json", params: ["address": address])

    guard let results = json["results"] as? [[String: Any]], let first = results.first,
          let geometry = first["geometry"] as? [String: Any],
          let location = geometry["location"] as? [String: Double],
          let lat = location["lat"], let lng = location["lng"],
          let formattedAddress = first["formatted_address"] as? String
    else {
        return "No results found for: \(address)"
    }

    return """
        Address: \(formattedAddress)
        Coordinates: \(lat), \(lng)
        """
}

func reverseGeocode(lat: Double, lng: Double) async throws -> String {
    let json = try await fetchJSON(
        endpoint: "geocode/json", params: ["latlng": "\(lat),\(lng)"])

    guard let results = json["results"] as? [[String: Any]], let first = results.first,
          let formattedAddress = first["formatted_address"] as? String
    else {
        return "No address found for: \(lat), \(lng)"
    }

    return "Address: \(formattedAddress)"
}

func searchPlaces(query: String, location: String?) async throws -> String {
    var params: [String: String] = ["query": query]
    if let loc = location {
        params["location"] = loc
        params["radius"] = "5000"
    }

    let json = try await fetchJSON(endpoint: "place/textsearch/json", params: params)

    guard let results = json["results"] as? [[String: Any]] else {
        return "No places found for: \(query)"
    }

    let places = results.prefix(5).compactMap { place -> String? in
        guard let name = place["name"] as? String,
              let address = place["formatted_address"] as? String
        else { return nil }
        let rating = place["rating"] as? Double ?? 0
        return "• \(name) (★\(String(format: "%.1f", rating)))\n  \(address)"
    }

    return places.joined(separator: "\n\n")
}

func placeDetails(placeId: String) async throws -> String {
    let json = try await fetchJSON(
        endpoint: "place/details/json",
        params: ["place_id": placeId, "fields": "name,formatted_address,rating,opening_hours,website,phone_number"]
    )

    guard let result = json["result"] as? [String: Any] else {
        return "Place not found"
    }

    let name = result["name"] as? String ?? "Unknown"
    let address = result["formatted_address"] as? String ?? ""
    let rating = result["rating"] as? Double ?? 0
    let website = result["website"] as? String ?? "N/A"
    let phone = result["formatted_phone_number"] as? String ?? "N/A"

    return """
        📍 \(name)
        Address: \(address)
        Rating: ★\(String(format: "%.1f", rating))
        Phone: \(phone)
        Website: \(website)
        """
}

func getDirections(origin: String, destination: String, mode: String) async throws -> String {
    let json = try await fetchJSON(
        endpoint: "directions/json",
        params: [
            "origin": origin, 
            "destination": destination, 
            "mode": mode,
            "departure_time": "now",
            "traffic_model": "best_guess"
        ]
    )

    guard let routes = json["routes"] as? [[String: Any]], let route = routes.first,
          let legs = route["legs"] as? [[String: Any]], let leg = legs.first,
          let distance = leg["distance"] as? [String: Any],
          let duration = leg["duration"] as? [String: Any],
          let steps = leg["steps"] as? [[String: Any]]
    else {
        return "No route found"
    }

    let distanceText = distance["text"] as? String ?? ""
    let durationText = duration["text"] as? String ?? ""
    let durationInTrafficText = leg["duration_in_traffic"] != nil ? (leg["duration_in_traffic"] as? [String: Any])?["text"] as? String : nil

    let directions = steps.prefix(10).compactMap { step -> String? in
        guard let instruction = step["html_instructions"] as? String else { return nil }
        // Strip HTML tags
        let clean =
            instruction
            .replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
        return "→ \(clean)"
    }

    var result = """
        🚗 Route: \(origin) → \(destination)
        Distance: \(distanceText)
        Duration: \(durationText)
        """
    
    if let traffic = durationInTrafficText {
        result += "\n        Duration in Traffic: \(traffic) (LIVE)"
    }

    result += "\n\n        Directions:\n        \(directions.joined(separator: "\n"))"
    return result
}

func getDistanceMatrix(origins: String, destinations: String) async throws -> String {
    let json = try await fetchJSON(
        endpoint: "distancematrix/json",
        params: [
            "origins": origins, 
            "destinations": destinations,
            "departure_time": "now",
            "traffic_model": "best_guess"
        ]
    )

    guard let rows = json["rows"] as? [[String: Any]], let row = rows.first,
          let elements = row["elements"] as? [[String: Any]], let element = elements.first,
          let distance = element["distance"] as? [String: Any],
          let duration = element["duration"] as? [String: Any]
    else {
        return "Could not calculate distance"
    }

    let distanceText = distance["text"] as? String ?? ""
    let durationText = duration["text"] as? String ?? ""
    let durationInTrafficText = (element["duration_in_traffic"] as? [String: Any])?["text"] as? String

    var result = """
        📏 Distance: \(distanceText)
        ⏱️ Duration: \(durationText)
        """
    
    if let traffic = durationInTrafficText {
        result += "\n        ⏱️ Duration in Traffic: \(traffic) (LIVE)"
    }
    
    return result
}

func getStreetView(location: String, heading: Int, pitch: Int, fov: Int, applyCyberpunk: Bool)
    async throws -> String
{
    let params: [String: String] = [
        "location": location,
        "size": "640x480",
        "heading": String(heading),
        "pitch": String(pitch),
        "fov": String(fov),
    ]

    let data = try await fetchGoogleMapsAPI(endpoint: "streetview", params: params)

    var finalData = data
    if applyCyberpunk {
        if let filtered = CyberpunkFilter.apply(to: data) {
            finalData = filtered
        }
    }

    // Save to screenshots folder
    let screenshotsDir =
        FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".config/atlastrinity/screenshots")
    try? FileManager.default.createDirectory(at: screenshotsDir, withIntermediateDirectories: true)

    let filename = "streetview_\(Int(Date().timeIntervalSince1970)).png"
    let filePath = screenshotsDir.appendingPathComponent(filename)
    try finalData.write(to: filePath)

    return """
        🌐 Street View captured!
        Location: \(location)
        Saved to: \(filePath.path)
        Cyberpunk filter: \(applyCyberpunk ? "Applied" : "Off")
        """
}

func getStaticMap(
    center: String, zoom: Int, mapType: String, markers: String?, applyCyberpunk: Bool
) async throws -> String {
    var params: [String: String] = [
        "center": center,
        "zoom": String(zoom),
        "size": "640x480",
        "maptype": mapType,
        "style": "feature:all|element:geometry|color:0x1a1a2e",  // Dark base
    ]

    if let markers = markers {
        params["markers"] = markers
    }

    let data = try await fetchGoogleMapsAPI(endpoint: "staticmap", params: params)

    var finalData = data
    if applyCyberpunk {
        if let filtered = CyberpunkFilter.apply(to: data) {
            finalData = filtered
        }
    }

    // Save to screenshots folder
    let screenshotsDir =
        FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".config/atlastrinity/screenshots")
    try? FileManager.default.createDirectory(at: screenshotsDir, withIntermediateDirectories: true)

    let filename = "staticmap_\(Int(Date().timeIntervalSince1970)).png"
    let filePath = screenshotsDir.appendingPathComponent(filename)
    try finalData.write(to: filePath)

    return """
        🗺️ Static Map generated!
        Center: \(center)
        Zoom: \(zoom)
        Type: \(mapType)
        Saved to: \(filePath.path)
        """
}

func getElevation(locations: String) async throws -> String {
    let json = try await fetchJSON(endpoint: "elevation/json", params: ["locations": locations])

    guard let results = json["results"] as? [[String: Any]] else {
        return "Elevation data not available"
    }

    let elevations = results.compactMap { result -> String? in
        guard let elevation = result["elevation"] as? Double,
              let location = result["location"] as? [String: Double],
              let lat = location["lat"], let lng = location["lng"]
        else { return nil }
        return "📍 (\(String(format: "%.4f", lat)), \(String(format: "%.4f", lng))): \(String(format: "%.1f", elevation))m"
    }

    return "Elevation Data:\n" + elevations.joined(separator: "\n")
}

// MARK: - Tool Schemas

let geocodeSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "address": .object([
            "type": .string("string"),
            "description": .string("Address to geocode (e.g., 'Kyiv, Ukraine')"),
        ])
    ]),
    "required": .array([.string("address")]),
])

let reverseGeocodeSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "lat": .object([
            "type": .string("number"),
            "description": .string("Latitude"),
        ]),
        "lng": .object([
            "type": .string("number"),
            "description": .string("Longitude"),
        ]),
    ]),
    "required": .array([.string("lat"), .string("lng")]),
])

let searchPlacesSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "query": .object([
            "type": .string("string"),
            "description": .string("Search query (e.g., 'restaurants near Maidan')"),
        ]),
        "location": .object([
            "type": .string("string"),
            "description": .string("Optional: center point as 'lat,lng'"),
        ]),
    ]),
    "required": .array([.string("query")]),
])

let placeDetailsSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "place_id": .object([
            "type": .string("string"),
            "description": .string("Google Place ID"),
        ])
    ]),
    "required": .array([.string("place_id")]),
])

let directionsSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "origin": .object([
            "type": .string("string"),
            "description": .string("Starting point address or coordinates"),
        ]),
        "destination": .object([
            "type": .string("string"),
            "description": .string("Destination address or coordinates"),
        ]),
        "mode": .object([
            "type": .string("string"),
            "description": .string("Travel mode: driving, walking, bicycling, transit"),
        ]),
    ]),
    "required": .array([.string("origin"), .string("destination")]),
    "description": .string("Get turn-by-turn directions with live traffic awareness (departure_time=now).")
])

let distanceMatrixSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "origins": .object([
            "type": .string("string"),
            "description": .string("Origin address(es), pipe-separated"),
        ]),
        "destinations": .object([
            "type": .string("string"),
            "description": .string("Destination address(es), pipe-separated"),
        ]),
    ]),
    "required": .array([.string("origins"), .string("destinations")]),
    "description": .string("Calculate travel distance and time with live traffic awareness (departure_time=now).")
])

let streetViewSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "location": .object([
            "type": .string("string"),
            "description": .string("Location as address or 'lat,lng'"),
        ]),
        "heading": .object([
            "type": .string("number"),
            "description": .string("Camera heading (0-360 degrees)"),
        ]),
        "pitch": .object([
            "type": .string("number"),
            "description": .string("Camera pitch (-90 to 90)"),
        ]),
        "fov": .object([
            "type": .string("number"),
            "description": .string("Field of view (10-120, default 90)"),
        ]),
        "cyberpunk": .object([
            "type": .string("boolean"),
            "description": .string("Apply Cyberpunk color filter (default: true)"),
        ]),
    ]),
    "required": .array([.string("location")]),
])

let staticMapSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "center": .object([
            "type": .string("string"),
            "description": .string("Map center as address or 'lat,lng'"),
        ]),
        "zoom": .object([
            "type": .string("number"),
            "description": .string("Zoom level (1-21)"),
        ]),
        "maptype": .object([
            "type": .string("string"),
            "description": .string("Map type: roadmap, satellite, terrain, hybrid"),
        ]),
        "markers": .object([
            "type": .string("string"),
            "description": .string("Optional markers specification"),
        ]),
        "cyberpunk": .object([
            "type": .string("boolean"),
            "description": .string("Apply Cyberpunk color filter (default: true)"),
        ]),
    ]),
    "required": .array([.string("center")]),
])

let elevationSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "locations": .object([
            "type": .string("string"),
            "description": .string("Locations as 'lat,lng' or 'lat,lng|lat,lng|...'"),
        ])
    ]),
    "required": .array([.string("locations")]),
])

let interactiveSearchSchema: Value = .object([
    "type": .string("object"),
    "properties": .object([
        "initial_query": .object([
            "type": .string("string"),
            "description": .string("Optional initial search query to pre-fill the search bar"),
        ])
    ]),
    "required": .array([]),
])

// MARK: - Helper Functions

func getRequiredString(from args: [String: Value]?, key: String) throws -> String {
    guard let val = args?[key]?.stringValue else {
        throw MCPError.invalidParams("Missing required argument: '\(key)'")
    }
    return val
}

func getOptionalString(from args: [String: Value]?, key: String) -> String? {
    return args?[key]?.stringValue
}

func getOptionalInt(from args: [String: Value]?, key: String, defaultValue: Int) -> Int {
    if let value = args?[key] {
        if let intVal = value.intValue {
            return intVal
        }
        if let doubleVal = value.doubleValue {
            return Int(doubleVal)
        }
    }
    return defaultValue
}

func getOptionalBool(from args: [String: Value]?, key: String, defaultValue: Bool) -> Bool {
    return args?[key]?.boolValue ?? defaultValue
}

// MARK: - Main Server Setup

func setupAndStartServer() async throws -> Server {
    fputs("log: Starting Google Maps MCP Server...\n", stderr)

    if GOOGLE_MAPS_API_KEY.isEmpty {
        fputs("warning: GOOGLE_MAPS_API_KEY not set!\n", stderr)
    }

    // Define tools
    let tools: [Tool] = [
        Tool(
            name: "maps_geocode",
            description: "Convert an address to geographic coordinates (latitude, longitude)",
            inputSchema: geocodeSchema
        ),
        Tool(
            name: "maps_reverse_geocode",
            description: "Convert coordinates to a human-readable address",
            inputSchema: reverseGeocodeSchema
        ),
        Tool(
            name: "maps_search_places",
            description: "Search for places, businesses, and points of interest",
            inputSchema: searchPlacesSchema
        ),
        Tool(
            name: "maps_place_details",
            description: "Get detailed information about a specific place",
            inputSchema: placeDetailsSchema
        ),
        Tool(
            name: "maps_directions",
            description: "Get turn-by-turn directions between two locations",
            inputSchema: directionsSchema
        ),
        Tool(
            name: "maps_distance_matrix",
            description: "Calculate travel distance and time between locations",
            inputSchema: distanceMatrixSchema
        ),
        Tool(
            name: "maps_street_view",
            description:
                "Get a Street View panoramic image with optional Cyberpunk styling",
            inputSchema: streetViewSchema
        ),
        Tool(
            name: "maps_static_map",
            description:
                "Generate a static map image with optional Cyberpunk styling",
            inputSchema: staticMapSchema
        ),
        Tool(
            name: "maps_elevation",
            description: "Get elevation data for specified locations",
            inputSchema: elevationSchema
        ),
        Tool(
            name: "maps_open_interactive_search",
            description: "Open the interactive map with autocomplete search bar in the Atlas UI",
            inputSchema: interactiveSearchSchema
        ),
    ]

    // Create server
    let server = Server(
        name: "mcp-server-googlemaps",
        version: "1.0.0",
        capabilities: .init(
            prompts: nil,
            resources: nil,
            tools: .init(listChanged: false)
        )
    )

    // Register tools list handler
    await server.withMethodHandler(ListTools.self) { _ in
        return .init(tools: tools)
    }

    // Register tool call handler
    await server.withMethodHandler(CallTool.self) { params in
        let args = params.arguments

        do {
            let result: String
            switch params.name {
            case "maps_geocode":
                let address = try getRequiredString(from: args, key: "address")
                result = try await geocode(address: address)

            case "maps_reverse_geocode":
                guard let lat = args?["lat"]?.doubleValue,
                      let lng = args?["lng"]?.doubleValue
                else {
                    throw MCPError.invalidParams("Missing lat/lng")
                }
                result = try await reverseGeocode(lat: lat, lng: lng)

            case "maps_search_places":
                let query = try getRequiredString(from: args, key: "query")
                let location = getOptionalString(from: args, key: "location")
                result = try await searchPlaces(query: query, location: location)

            case "maps_place_details":
                let placeId = try getRequiredString(from: args, key: "place_id")
                result = try await placeDetails(placeId: placeId)

            case "maps_directions":
                let origin = try getRequiredString(from: args, key: "origin")
                let destination = try getRequiredString(from: args, key: "destination")
                let mode = getOptionalString(from: args, key: "mode") ?? "driving"
                result = try await getDirections(origin: origin, destination: destination, mode: mode)

            case "maps_distance_matrix":
                let origins = try getRequiredString(from: args, key: "origins")
                let destinations = try getRequiredString(from: args, key: "destinations")
                result = try await getDistanceMatrix(origins: origins, destinations: destinations)

            case "maps_street_view":
                let location = try getRequiredString(from: args, key: "location")
                let heading = getOptionalInt(from: args, key: "heading", defaultValue: 0)
                let pitch = getOptionalInt(from: args, key: "pitch", defaultValue: 0)
                let fov = getOptionalInt(from: args, key: "fov", defaultValue: 90)
                let cyberpunk = getOptionalBool(from: args, key: "cyberpunk", defaultValue: true)
                result = try await getStreetView(
                    location: location, heading: heading, pitch: pitch, fov: fov,
                    applyCyberpunk: cyberpunk)

            case "maps_static_map":
                let center = try getRequiredString(from: args, key: "center")
                let zoom = getOptionalInt(from: args, key: "zoom", defaultValue: 15)
                let mapType = getOptionalString(from: args, key: "maptype") ?? "roadmap"
                let markers = getOptionalString(from: args, key: "markers")
                let cyberpunk = getOptionalBool(from: args, key: "cyberpunk", defaultValue: true)
                result = try await getStaticMap(
                    center: center, zoom: zoom, mapType: mapType, markers: markers,
                    applyCyberpunk: cyberpunk)

            case "maps_elevation":
                let locations = try getRequiredString(from: args, key: "locations")
                result = try await getElevation(locations: locations)

            case "maps_open_interactive_search":
                let query = getOptionalString(from: args, key: "initial_query") ?? ""
                result = "🌐 INTERACTIVE_MAP_OPEN: \(query)"

            default:
                return .init(content: [.text("Unknown tool: \(params.name)")], isError: true)
            }

            return .init(content: [.text(result)], isError: false)

        } catch let error as MCPError {
            return .init(content: [.text("Error: \(error)")], isError: true)
        } catch {
            return .init(content: [.text("Error: \(error.localizedDescription)")], isError: true)
        }
    }

    // Start server with stdio transport
    let transport = StdioTransport()
    try await server.start(transport: transport)

    fputs("log: Google Maps MCP Server started successfully!\n", stderr)
    return server
}

// MARK: - Entry Point

@main
struct GoogleMapsMCPServer {
    static func main() async throws {
        let _ = try await setupAndStartServer()

        // Keep running until terminated
        await withCheckedContinuation { (_: CheckedContinuation<Void, Never>) in
            // Server runs indefinitely via stdio
        }
    }
}
