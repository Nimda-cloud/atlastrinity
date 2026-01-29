// The Swift Programming Language
// https://docs.swift.org/swift-book

import Foundation
import CoreWLAN

/// WiFiScanner provides Wi-Fi network scanning and analysis capabilities
@available(macOS 13.0, *)
public class WiFiScanner {
    
    /// Shared instance for singleton access
    public static let shared = WiFiScanner()
    
    /// CoreWLAN client interface
    private let client: CWWiFiClient
    
    /// Current Wi-Fi interface
    private var interface: CWInterface?
    
    /// Initializes the Wi-Fi scanner
    public init() {
        self.client = CWWiFiClient.shared()
        self.interface = client.interface()
    }
    
    /// Scans for available Wi-Fi networks
    /// - Returns: Array of WiFiNetwork objects representing available networks
    /// - Throws: WiFiScannerError if scanning fails
    public func scanForNetworks() throws -> [WiFiNetwork] {
        guard let interface = interface else {
            throw WiFiScannerError.noWiFiInterface
        }
        
        guard let networks = interface.scanForNetworks(withName: nil) else {
            throw WiFiScannerError.scanFailed
        }
        
        return networks.map { network in
            WiFiNetwork(
                ssid: network.ssid ?? "Unknown",
                bssid: network.bssid ?? "Unknown",
                rssi: network.rssiValue,
                channel: network.wlanChannel?.channelNumber ?? 0,
                security: network.securityDescription,
                ibss: network.ibss
            )
        }
    }
    
    /// Gets information about the currently connected Wi-Fi network
    /// - Returns: WiFiNetwork object representing the current connection, or nil if not connected
    public func getCurrentNetwork() -> WiFiNetwork? {
        guard let interface = interface,
              let network = interface.ssid() else {
            return nil
        }
        
        return WiFiNetwork(
            ssid: network,
            bssid: interface.bssid() ?? "Unknown",
            rssi: interface.rssiValue(),
            channel: interface.wlanChannel()?.channelNumber ?? 0,
            security: interface.securityDescription(),
            ibss: interface.ibss()
        )
    }
    
    /// Gets detailed information about a specific Wi-Fi network
    /// - Parameter ssid: The SSID of the network to get information about
    /// - Returns: WiFiNetwork object with detailed information, or nil if network not found
    public func getNetworkDetails(for ssid: String) -> WiFiNetwork? {
        guard let interface = interface,
              let network = interface.network(withSSID: ssid) else {
            return nil
        }
        
        return WiFiNetwork(
            ssid: network.ssid ?? "Unknown",
            bssid: network.bssid ?? "Unknown",
            rssi: network.rssiValue,
            channel: network.wlanChannel?.channelNumber ?? 0,
            security: network.securityDescription,
            ibss: network.ibss
        )
    }
    
    /// Checks if Wi-Fi is enabled
    /// - Returns: Boolean indicating whether Wi-Fi is enabled
    public func isWiFiEnabled() -> Bool {
        return interface?.powerOn() ?? false
    }
    
    /// Enables or disables Wi-Fi
    /// - Parameter enabled: Boolean indicating whether to enable or disable Wi-Fi
    /// - Throws: WiFiScannerError if operation fails
    public func setWiFiEnabled(_ enabled: Bool) throws {
        guard let interface = interface else {
            throw WiFiScannerError.noWiFiInterface
        }
        
        try interface.setPower(enabled)
    }
}

/// WiFiNetwork represents a Wi-Fi network with its properties
@available(macOS 13.0, *)
public struct WiFiNetwork: Identifiable {
    public let id = UUID()
    public let ssid: String
    public let bssid: String
    public let rssi: Int
    public let channel: Int
    public let security: String
    public let ibss: Bool
    
    /// Initializes a WiFiNetwork object
    /// - Parameters:
    ///   - ssid: Service Set Identifier (network name)
    ///   - bssid: Basic Service Set Identifier (MAC address)
    ///   - rssi: Received Signal Strength Indicator
    ///   - channel: Wi-Fi channel number
    ///   - security: Security protocol description
    ///   - ibss: Whether the network is Independent Basic Service Set (ad-hoc)
    public init(ssid: String, bssid: String, rssi: Int, channel: Int, security: String, ibss: Bool) {
        self.ssid = ssid
        self.bssid = bssid
        self.rssi = rssi
        self.channel = channel
        self.security = security
        self.ibss = ibss
    }
}

/// WiFiScannerError represents errors that can occur during Wi-Fi scanning
@available(macOS 13.0, *)
public enum WiFiScannerError: Error {
    case noWiFiInterface
    case scanFailed
    case powerChangeFailed
    case networkNotFound
    
    /// Human-readable description of the error
    public var localizedDescription: String {
        switch self {
        case .noWiFiInterface:
            return "No Wi-Fi interface available"
        case .scanFailed:
            return "Failed to scan for Wi-Fi networks"
        case .powerChangeFailed:
            return "Failed to change Wi-Fi power state"
        case .networkNotFound:
            return "Wi-Fi network not found"
        }
    }
}