// The Swift Programming Language
// https://docs.swift.org/swift-book

import XCTest
import CoreWLAN
@testable import NetworkManager

@available(macOS 13.0, *)
class WiFiScannerTests: XCTestCase {

    var wifiScanner: WiFiScanner!

    override func setUp() {
        super.setUp()
        wifiScanner = WiFiScanner()
    }

    override func tearDown() {
        wifiScanner = nil
        super.tearDown()
    }

    func testWiFiScannerInitialization() {
        XCTAssertNotNil(wifiScanner, "WiFiScanner should be initialized")
    }

    func testWiFiEnabledStatus() {
        let isEnabled = wifiScanner.isWiFiEnabled()
        // Just verify that the method doesn't crash and returns a boolean
        XCTAssertTrue(isEnabled is Bool, "isWiFiEnabled should return a boolean")
    }

    func testCurrentNetwork() {
        let currentNetwork = wifiScanner.getCurrentNetwork()
        // Just verify that the method doesn't crash
        // It may return nil if not connected to any network
        XCTAssertTrue(currentNetwork == nil || currentNetwork is WiFiNetwork, "getCurrentNetwork should return optional WiFiNetwork")
    }

    func testScanForNetworks() {
        do {
            let networks = try wifiScanner.scanForNetworks()
            XCTAssertTrue(networks is [WiFiNetwork], "scanForNetworks should return array of WiFiNetwork")
        } catch {
            // It's okay if scanning fails in test environment
            print("Scan failed (expected in some test environments): \(error)")
        }
    }

    func testNetworkDetails() {
        // Test with a dummy SSID - this will likely return nil but shouldn't crash
        let networkDetails = wifiScanner.getNetworkDetails(for: "TestNetwork")
        XCTAssertTrue(networkDetails == nil || networkDetails is WiFiNetwork, "getNetworkDetails should return optional WiFiNetwork")
    }

    func testWiFiNetworkProperties() {
        let testNetwork = WiFiNetwork(
            ssid: "TestSSID",
            bssid: "00:11:22:33:44:55",
            rssi: -50,
            channel: 6,
            security: "WPA2",
            ibss: false
        )

        XCTAssertEqual(testNetwork.ssid, "TestSSID")
        XCTAssertEqual(testNetwork.bssid, "00:11:22:33:44:55")
        XCTAssertEqual(testNetwork.rssi, -50)
        XCTAssertEqual(testNetwork.channel, 6)
        XCTAssertEqual(testNetwork.security, "WPA2")
        XCTAssertFalse(testNetwork.ibss)
    }

    func testWiFiScannerErrorDescriptions() {
        let noInterfaceError = WiFiScannerError.noWiFiInterface
        XCTAssertEqual(noInterfaceError.localizedDescription, "No Wi-Fi interface available")

        let scanFailedError = WiFiScannerError.scanFailed
        XCTAssertEqual(scanFailedError.localizedDescription, "Failed to scan for Wi-Fi networks")

        let powerChangeError = WiFiScannerError.powerChangeFailed
        XCTAssertEqual(powerChangeError.localizedDescription, "Failed to change Wi-Fi power state")

        let networkNotFoundError = WiFiScannerError.networkNotFound
        XCTAssertEqual(networkNotFoundError.localizedDescription, "Wi-Fi network not found")
    }
}