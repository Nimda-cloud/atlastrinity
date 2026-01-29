// The Swift Programming Language
// https://docs.swift.org/swift-book

/// NetworkManager provides network utilities, SSH communication, packet inspection, and bandwidth monitoring capabilities
@available(macOS 13.0, *)
public class NetworkManager {
    
    /// Shared instance for singleton access
    public static let shared = NetworkManager()
    
    /// SSH Manager instance
    public lazy var ssh: SSHManager = {
        return SSHManager()
    }()
    
    /// Wi-Fi Scanner instance
    public lazy var wifi: WiFiScanner = {
        return WiFiScanner()
    }()

    /// Packet Inspector instance
    public lazy var packetInspector: PacketInspector = {
        return PacketInspector()
    }()

    /// Bandwidth Monitor instance
    public lazy var bandwidthMonitor: BandwidthMonitor = {
        return BandwidthMonitor()
    }()

    /// Deep Analysis Module instance
    public lazy var deepAnalysis: DeepAnalysisModule = {
        return DeepAnalysisModule()
    }()

    private init() {}
    
    /// Initialize NetworkManager with custom configuration
    /// - Returns: Configured NetworkManager instance
    public static func initialize() -> NetworkManager {
        return shared
    }
}
