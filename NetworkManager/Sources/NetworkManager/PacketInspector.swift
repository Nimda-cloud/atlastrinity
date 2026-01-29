//  PacketInspector.swift
//  NetworkManager
//
//  Created by AtlasTrinity on 2024-01-01.
//  Copyright © 2024 AtlasTrinity. All rights reserved.

import Foundation
import Network
import SwiftUI

/// PacketInspector provides deep packet inspection and analysis capabilities
@available(macOS 13.0, *)
public class PacketInspector: NSObject, ObservableObject {

    // MARK: - Properties

    /// Shared instance for singleton access
    public static let shared = PacketInspector()

    /// Current inspection status
    @Published public var isInspecting: Bool = false

    /// Inspection status message
    @Published public var inspectionStatus: String = "Not inspecting"

    /// Captured packets
    @Published public var capturedPackets: [NetworkPacket] = []

    /// Packet statistics
    @Published public var packetStatistics: PacketStatistics = PacketStatistics()

    /// Error messages
    @Published public var errorMessage: String = ""

    /// Network monitor for packet capture
    private var networkMonitor: NWPathMonitor?

    /// Dispatch queue for thread safety
    private let inspectionQueue = DispatchQueue(label: "com.atlastrinity.packetinspector", attributes: .concurrent)

    /// Packet capture session
    private var packetCaptureSession: PacketCaptureSession?

    // MARK: - Initialization

    public override init() {
        super.init()
    }

    deinit {
        stopInspection()
    }

    // MARK: - Packet Inspection Management

    /// Start packet inspection on a specific interface
    /// - Parameters:
    ///   - interfaceName: Name of the network interface to monitor
    ///   - filter: BPF filter for packet capture (optional)
    ///   - maxPackets: Maximum number of packets to capture (0 for unlimited)
    public func startInspection(
        interfaceName: String = "en0",
        filter: String? = nil,
        maxPackets: Int = 0
    ) {
        inspectionQueue.async(flags: .barrier) { [weak self] in
            guard let self = self else { return }

            self.stopInspection() // Ensure clean start

            do {
                // Create packet capture session
                self.packetCaptureSession = try PacketCaptureSession(
                    interfaceName: interfaceName,
                    filter: filter,
                    maxPackets: maxPackets
                )

                // Set up packet handler
                self.packetCaptureSession?.onPacketReceived = { [weak self] packet in
                    self?.handleReceivedPacket(packet)
                }

                self.packetCaptureSession?.onError = { [weak self] error in
                    self?.handleError(error)
                }

                self.packetCaptureSession?.onStatisticsUpdate = { [weak self] statistics in
                    self?.updateStatistics(statistics)
                }

                // Start capture
                try self.packetCaptureSession?.start()

                self.updateInspectionStatus(inspecting: true, interface: interfaceName)

            } catch {
                self.handleError(error)
            }
        }
    }

    /// Stop packet inspection
    public func stopInspection() {
        inspectionQueue.async(flags: .barrier) { [weak self] in
            guard let self = self else { return }

            self.packetCaptureSession?.stop()
            self.packetCaptureSession = nil

            self.updateInspectionStatus(inspecting: false, interface: nil)
        }
    }

    /// Clear captured packets and statistics
    public func clearData() {
        inspectionQueue.async(flags: .barrier) { [weak self] in
            guard let self = self else { return }

            self.capturedPackets.removeAll()
            self.packetStatistics = PacketStatistics()
        }
    }

    // MARK: - Packet Analysis

    /// Analyze captured packets and generate report
    /// - Returns: PacketAnalysisReport containing analysis results
    public func analyzePackets() -> PacketAnalysisReport {
        return inspectionQueue.sync {
            var report = PacketAnalysisReport()

            // Basic statistics
            report.totalPackets = capturedPackets.count
            report.startTime = capturedPackets.first?.timestamp ?? Date()
            report.endTime = capturedPackets.last?.timestamp ?? Date()

            // Protocol distribution
            var protocolCounts: [String: Int] = [:]
            for packet in capturedPackets {
                let packetProtocol = packet.packetProtocol ?? "Unknown"
                protocolCounts[packetProtocol] = (protocolCounts[packetProtocol] ?? 0) + 1
            }
            report.protocolDistribution = protocolCounts

            // IP address analysis
            var sourceIPs: [String: Int] = [:]
            var destinationIPs: [String: Int] = [:]
            for packet in capturedPackets {
                if let sourceIP = packet.sourceIP {
                    sourceIPs[sourceIP] = (sourceIPs[sourceIP] ?? 0) + 1
                }
                if let destinationIP = packet.destinationIP {
                    destinationIPs[destinationIP] = (destinationIPs[destinationIP] ?? 0) + 1
                }
            }
            report.sourceIPDistribution = sourceIPs
            report.destinationIPDistribution = destinationIPs

            // Port analysis
            var sourcePorts: [Int: Int] = [:]
            var destinationPorts: [Int: Int] = [:]
            for packet in capturedPackets {
                if let sourcePort = packet.sourcePort {
                    sourcePorts[sourcePort] = (sourcePorts[sourcePort] ?? 0) + 1
                }
                if let destinationPort = packet.destinationPort {
                    destinationPorts[destinationPort] = (destinationPorts[destinationPort] ?? 0) + 1
                }
            }
            report.sourcePortDistribution = sourcePorts
            report.destinationPortDistribution = destinationPorts

            // Calculate duration
            if capturedPackets.count > 1 {
                report.duration = report.endTime.timeIntervalSince(report.startTime)
            }

            return report
        }
    }

    /// Export captured packets to PCAP file
    /// - Parameter fileURL: URL to save the PCAP file
    /// - Throws: PacketInspectorError if export fails
    public func exportToPCAP(fileURL: URL) throws {
        try inspectionQueue.sync(flags: .barrier) {
            guard !capturedPackets.isEmpty else {
                throw PacketInspectorError.noPacketsToExport
            }

            // Create PCAP file header
            var pcapHeader = PCAPHeader()
            pcapHeader.magicNumber = 0xA1B2C3D4
            pcapHeader.versionMajor = 2
            pcapHeader.versionMinor = 4
            pcapHeader.thiszone = 0
            pcapHeader.sigfigs = 0
            pcapHeader.snaplen = 65535
            pcapHeader.network = 1 // Ethernet

            // Write to file
            let fileManager = FileManager.default
            if fileManager.fileExists(atPath: fileURL.path) {
                try fileManager.removeItem(at: fileURL)
            }

            guard fileManager.createFile(atPath: fileURL.path, contents: nil) else {
                throw PacketInspectorError.fileCreationFailed
            }

            let fileHandle = try FileHandle(forWritingTo: fileURL)
            defer { fileHandle.closeFile() }

            // Write header
            var headerData = Data()
            withUnsafeBytes(of: &pcapHeader) { headerData.append(contentsOf: $0) }
            try fileHandle.write(contentsOf: headerData)

            // Write packets
            for packet in capturedPackets {
                guard let packetData = packet.rawData else { continue }

                // Create PCAP record header
                var recordHeader = PCAPRecordHeader()
                recordHeader.tsSec = UInt32(packet.timestamp.timeIntervalSince1970)
                recordHeader.tsUsec = UInt32((packet.timestamp.timeIntervalSince1970.truncatingRemainder(dividingBy: 1)) * 1_000_000)
                recordHeader.inclLen = UInt32(packetData.count)
                recordHeader.origLen = UInt32(packetData.count)

                // Write record header
                var recordHeaderData = Data()
                withUnsafeBytes(of: &recordHeader) { recordHeaderData.append(contentsOf: $0) }
                try fileHandle.write(contentsOf: recordHeaderData)

                // Write packet data
                try fileHandle.write(contentsOf: packetData)
            }
        }
    }

    // MARK: - Private Methods

    /// Handle received packet
    /// - Parameter packet: Received network packet
    private func handleReceivedPacket(_ packet: NetworkPacket) {
        inspectionQueue.async { [weak self] in
            guard let self = self else { return }

            // Add to captured packets
            self.capturedPackets.append(packet)

            // Update statistics
            self.packetStatistics.totalPackets += 1
            self.packetStatistics.totalBytes += packet.length

            if let packetProtocol = packet.protocol {
                self.packetStatistics.protocolCounts[packetProtocol] = (self.packetStatistics.protocolCounts[packetProtocol] ?? 0) + 1
            }

            // Limit captured packets if maxPackets is set
            if let maxPackets = self.packetCaptureSession?.maxPackets, 
               maxPackets > 0, 
               self.capturedPackets.count >= maxPackets {
                self.stopInspection()
            }
        }
    }

    /// Update packet statistics
    /// - Parameter statistics: Updated statistics
    private func updateStatistics(_ statistics: PacketStatistics) {
        inspectionQueue.async { [weak self] in
            guard let self = self else { return }
            self.packetStatistics = statistics
        }
    }

    /// Update inspection status on main thread
    /// - Parameters:
    ///   - inspecting: Inspection status
    ///   - interface: Interface name (optional)
    private func updateInspectionStatus(inspecting: Bool, interface: String?) {
        DispatchQueue.main.async { [weak self] in
            self?.isInspecting = inspecting
            if inspecting, let interface = interface {
                self?.inspectionStatus = "Inspecting on \(interface)"
            } else {
                self?.inspectionStatus = "Not inspecting"
            }
        }
    }

    /// Handle errors and update error message
    /// - Parameter error: Error to handle
    private func handleError(_ error: Error) {
        DispatchQueue.main.async { [weak self] in
            if let packetError = error as? PacketInspectorError {
                self?.errorMessage = packetError.localizedDescription
            } else {
                self?.errorMessage = error.localizedDescription
            }
            self?.isInspecting = false
            self?.inspectionStatus = "Inspection failed"
        }
    }

    // MARK: - Error Handling

    /// PacketInspector-specific errors
    public enum PacketInspectorError: Error {
        case notInspecting
        case inspectionFailed(String)
        case invalidInterface(String)
        case invalidFilter(String)
        case permissionDenied
        case noPacketsToExport
        case fileCreationFailed
        case fileWriteFailed
        case unknownError

        public var localizedDescription: String {
            switch self {
            case .notInspecting:
                return "Packet inspection is not active"
            case .inspectionFailed(let message):
                return "Inspection failed: \(message)"
            case .invalidInterface(let interface):
                return "Invalid network interface: \(interface)"
            case .invalidFilter(let filter):
                return "Invalid BPF filter: \(filter)"
            case .permissionDenied:
                return "Permission denied for packet capture"
            case .noPacketsToExport:
                return "No packets available for export"
            case .fileCreationFailed:
                return "Failed to create export file"
            case .fileWriteFailed:
                return "Failed to write to export file"
            case .unknownError:
                return "Unknown packet inspection error"
            }
        }
    }
}

// MARK: - Supporting Types

/// NetworkPacket represents a captured network packet
@available(macOS 13.0, *)
public struct NetworkPacket: Identifiable {
    public let id = UUID()
    public let timestamp: Date
    public let sourceIP: String?
    public let destinationIP: String?
    public let sourcePort: Int?
    public let destinationPort: Int?
    public let packetProtocol: String?
    public let length: Int
    public let rawData: Data?
    public let interface: String

    public init(
        timestamp: Date,
        sourceIP: String?,
        destinationIP: String?,
        sourcePort: Int?,
        destinationPort: Int?,
        protocol: String?,
        length: Int,
        rawData: Data?,
        interface: String
    ) {
        self.timestamp = timestamp
        self.sourceIP = sourceIP
        self.destinationIP = destinationIP
        self.sourcePort = sourcePort
        self.destinationPort = destinationPort
        self.packetProtocol = packetProtocol
        self.length = length
        self.rawData = rawData
        self.interface = interface
    }
}

/// PacketStatistics contains statistics about captured packets
@available(macOS 13.0, *)
public struct PacketStatistics {
    public var totalPackets: Int = 0
    public var totalBytes: Int = 0
    public var protocolCounts: [String: Int] = [:]
    public var startTime: Date?
    public var endTime: Date?

    public init() {}

    public init(totalPackets: Int, totalBytes: Int, protocolCounts: [String : Int], startTime: Date?, endTime: Date?) {
        self.totalPackets = totalPackets
        self.totalBytes = totalBytes
        self.protocolCounts = protocolCounts
        self.startTime = startTime
        self.endTime = endTime
    }
}

/// PacketAnalysisReport contains analysis results
@available(macOS 13.0, *)
public struct PacketAnalysisReport {
    public var totalPackets: Int = 0
    public var startTime: Date = Date()
    public var endTime: Date = Date()
    public var duration: TimeInterval = 0
    public var protocolDistribution: [String: Int] = [:]
    public var sourceIPDistribution: [String: Int] = [:]
    public var destinationIPDistribution: [String: Int] = [:]
    public var sourcePortDistribution: [Int: Int] = [:]
    public var destinationPortDistribution: [Int: Int] = [:]

    public init() {}
}

/// PacketCaptureSession handles low-level packet capture
@available(macOS 13.0, *)
private class PacketCaptureSession {
    let interfaceName: String
    let filter: String?
    let maxPackets: Int
    var onPacketReceived: ((NetworkPacket) -> Void)?
    var onError: ((Error) -> Void)?
    var onStatisticsUpdate: ((PacketStatistics) -> Void)?

    private var isRunning: Bool = false

    init(interfaceName: String, filter: String?, maxPackets: Int) {
        self.interfaceName = interfaceName
        self.filter = filter
        self.maxPackets = maxPackets
    }

    func start() throws {
        // In a real implementation, this would use libpcap or similar
        // For this demo, we'll simulate packet capture
        isRunning = true

        DispatchQueue.global().async { [weak self] in
            guard let self = self else { return }

            // Simulate packet capture
            var packetCount = 0
            let protocols = ["TCP", "UDP", "ICMP", "HTTP", "DNS"]

            while self.isRunning && (self.maxPackets == 0 || packetCount < self.maxPackets) {
                // Simulate receiving a packet
                let packetProtocol = protocols.randomElement() ?? "TCP"
                let sourceIP = "192.168.1." + String(Int.random(in: 10...100))
                let destinationIP = "10.0.0." + String(Int.random(in: 10...100))
                let sourcePort = Int.random(in: 1024...65535)
                let destinationPort = Int.random(in: 1...1023)
                let length = Int.random(in: 64...1500)

                let packet = NetworkPacket(
                    timestamp: Date(),
                    sourceIP: sourceIP,
                    destinationIP: destinationIP,
                    sourcePort: sourcePort,
                    destinationPort: destinationPort,
                    packetProtocol: packetProtocol,
                    length: length,
                    rawData: nil,
                    interface: self.interfaceName
                )

                self.onPacketReceived?(packet)
                packetCount += 1

                // Simulate network traffic timing
                Thread.sleep(forTimeInterval: Double.random(in: 0.01...0.1))
            }

            if self.isRunning {
                self.isRunning = false
                self.onError?(PacketInspectorError.inspectionFailed("Capture completed"))
            }
        }
    }

    func stop() {
        isRunning = false
    }
}

// MARK: - PCAP File Structures

/// PCAP file header structure
private struct PCAPHeader {
    var magicNumber: UInt32 = 0
    var versionMajor: UInt16 = 0
    var versionMinor: UInt16 = 0
    var thiszone: Int32 = 0
    var sigfigs: UInt32 = 0
    var snaplen: UInt32 = 0
    var network: UInt32 = 0
}

/// PCAP record header structure
private struct PCAPRecordHeader {
    var tsSec: UInt32 = 0
    var tsUsec: UInt32 = 0
    var inclLen: UInt32 = 0
    var origLen: UInt32 = 0
}