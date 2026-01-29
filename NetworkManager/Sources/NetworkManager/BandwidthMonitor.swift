//  BandwidthMonitor.swift
//  NetworkManager
//
//  Created by AtlasTrinity on 2024-01-01.
//  Copyright © 2024 AtlasTrinity. All rights reserved.

import Foundation
import Network
import SwiftUI

/// BandwidthMonitor provides bandwidth usage monitoring and analysis capabilities
@available(macOS 13.0, *)
public class BandwidthMonitor: NSObject, ObservableObject {

    // MARK: - Properties

    /// Shared instance for singleton access
    public static let shared = BandwidthMonitor()

    /// Current monitoring status
    @Published public var isMonitoring: Bool = false

    /// Monitoring status message
    @Published public var monitoringStatus: String = "Not monitoring"

    /// Bandwidth usage history
    @Published public var bandwidthHistory: [BandwidthSample] = []

    /// Current bandwidth usage
    @Published public var currentUsage: BandwidthUsage = BandwidthUsage()

    /// Error messages
    @Published public var errorMessage: String = ""

    /// Network interfaces being monitored
    private var monitoredInterfaces: [String] = ["en0", "en1", "lo0"]

    /// Dispatch queue for thread safety
    private let monitoringQueue = DispatchQueue(label: "com.atlastrinity.bandwidthmonitor", attributes: .concurrent)

    /// Monitoring timer
    private var monitoringTimer: Timer?

    /// Previous network statistics for delta calculation
    private var previousStats: [String: NetworkInterfaceStats] = [:]

    // MARK: - Initialization

    public override init() {
        super.init()
    }

    deinit {
        stopMonitoring()
    }

    // MARK: - Bandwidth Monitoring Management

    /// Start bandwidth monitoring
    /// - Parameters:
    ///   - interfaces: Array of interface names to monitor
    ///   - interval: Sampling interval in seconds (default: 1.0)
    ///   - historyLimit: Maximum number of samples to keep in history (default: 60)
    public func startMonitoring(
        interfaces: [String] = ["en0", "en1", "lo0"],
        interval: TimeInterval = 1.0,
        historyLimit: Int = 60
    ) {
        monitoringQueue.async(flags: .barrier) { [weak self] in
            guard let self = self else { return }

            self.stopMonitoring() // Ensure clean start

            self.monitoredInterfaces = interfaces
            self.bandwidthHistory.removeAll()
            self.previousStats.removeAll()

            // Initialize previous stats
            for interface in interfaces {
                if let stats = self.getNetworkStats(for: interface) {
                    self.previousStats[interface] = stats
                }
            }

            // Start monitoring timer
            self.monitoringTimer = Timer.scheduledTimer(
                withTimeInterval: interval,
                repeats: true
            ) { [weak self] _ in
                self?.captureBandwidthSample()
            }

            self.updateMonitoringStatus(monitoring: true)
        }
    }

    /// Stop bandwidth monitoring
    public func stopMonitoring() {
        monitoringQueue.async(flags: .barrier) { [weak self] in
            guard let self = self else { return }

            self.monitoringTimer?.invalidate()
            self.monitoringTimer = nil

            self.updateMonitoringStatus(monitoring: false)
        }
    }

    /// Clear bandwidth history
    public func clearHistory() {
        monitoringQueue.async(flags: .barrier) { [weak self] in
            guard let self = self else { return }

            self.bandwidthHistory.removeAll()
            self.currentUsage = BandwidthUsage()
        }
    }

    // MARK: - Bandwidth Analysis

    /// Get current bandwidth usage summary
    /// - Returns: BandwidthSummary containing aggregated usage data
    public func getBandwidthSummary() -> BandwidthSummary {
        return monitoringQueue.sync {
            var summary = BandwidthSummary()

            // Calculate totals
            for sample in bandwidthHistory {
                summary.totalBytesSent += sample.bytesSent
                summary.totalBytesReceived += sample.bytesReceived
                summary.totalPacketsSent += sample.packetsSent
                summary.totalPacketsReceived += sample.packetsReceived
            }

            // Calculate averages
            if !bandwidthHistory.isEmpty {
                let sampleCount = Double(bandwidthHistory.count)
                summary.averageBytesSent = Double(summary.totalBytesSent) / sampleCount
                summary.averageBytesReceived = Double(summary.totalBytesReceived) / sampleCount
                summary.averagePacketsSent = Double(summary.totalPacketsSent) / sampleCount
                summary.averagePacketsReceived = Double(summary.totalPacketsReceived) / sampleCount
            }

            // Calculate peak usage
            for sample in bandwidthHistory {
                summary.peakBytesSent = max(summary.peakBytesSent, sample.bytesSent)
                summary.peakBytesReceived = max(summary.peakBytesReceived, sample.bytesReceived)
                summary.peakPacketsSent = max(summary.peakPacketsSent, sample.packetsSent)
                summary.peakPacketsReceived = max(summary.peakPacketsReceived, sample.packetsReceived)
            }

            // Set time range
            if let firstSample = bandwidthHistory.first, 
               let lastSample = bandwidthHistory.last {
                summary.startTime = firstSample.timestamp
                summary.endTime = lastSample.timestamp
                summary.duration = lastSample.timestamp.timeIntervalSince(firstSample.timestamp)
            }

            return summary
        }
    }

    /// Generate bandwidth usage report
    /// - Returns: BandwidthReport containing detailed analysis
    public func generateBandwidthReport() -> BandwidthReport {
        return monitoringQueue.sync {
            let summary = self.getBandwidthSummary()
            var report = BandwidthReport(summary: summary)

            // Interface-specific analysis
            var interfaceStats: [String: InterfaceBandwidthStats] = [:]
            for interface in monitoredInterfaces {
                var stats = InterfaceBandwidthStats(interface: interface)

                for sample in bandwidthHistory {
                    if let interfaceSample = sample.interfaceStats[interface] {
                        stats.totalBytesSent += interfaceSample.bytesSent
                        stats.totalBytesReceived += interfaceSample.bytesReceived
                        stats.totalPacketsSent += interfaceSample.packetsSent
                        stats.totalPacketsReceived += interfaceSample.packetsReceived
                    }
                }

                interfaceStats[interface] = stats
            }

            report.interfaceStats = interfaceStats

            // Calculate usage patterns
            report.usagePatterns = self.analyzeUsagePatterns()

            return report
        }
    }

    // MARK: - Private Methods

    /// Capture a bandwidth sample
    private func captureBandwidthSample() {
        monitoringQueue.async { [weak self] in
            guard let self = self else { return }

            var sample = BandwidthSample(timestamp: Date())
            var totalBytesSent: Int64 = 0
            var totalBytesReceived: Int64 = 0
            var totalPacketsSent: Int64 = 0
            var totalPacketsReceived: Int64 = 0

            // Capture stats for each interface
            for interface in self.monitoredInterfaces {
                if let currentStats = self.getNetworkStats(for: interface), 
                   let previousStats = self.previousStats[interface] {

                    // Calculate deltas
                    let bytesSent = currentStats.bytesOut - previousStats.bytesOut
                    let bytesReceived = currentStats.bytesIn - previousStats.bytesIn
                    let packetsSent = currentStats.packetsOut - previousStats.packetsOut
                    let packetsReceived = currentStats.packetsIn - previousStats.packetsIn

                    // Update interface stats
                    let interfaceSample = InterfaceBandwidthSample(
                        interface: interface,
                        bytesSent: bytesSent,
                        bytesReceived: bytesReceived,
                        packetsSent: packetsSent,
                        packetsReceived: packetsReceived
                    )

                    sample.interfaceStats[interface] = interfaceSample

                    // Accumulate totals
                    totalBytesSent += bytesSent
                    totalBytesReceived += bytesReceived
                    totalPacketsSent += packetsSent
                    totalPacketsReceived += packetsReceived

                    // Update previous stats
                    self.previousStats[interface] = currentStats
                }
            }

            // Set sample totals
            sample.bytesSent = totalBytesSent
            sample.bytesReceived = totalBytesReceived
            sample.packetsSent = totalPacketsSent
            sample.packetsReceived = totalPacketsReceived

            // Add to history
            self.bandwidthHistory.append(sample)

            // Update current usage
            self.currentUsage.bytesSent = Double(totalBytesSent)
            self.currentUsage.bytesReceived = Double(totalBytesReceived)
            self.currentUsage.packetsSent = Double(totalPacketsSent)
            self.currentUsage.packetsReceived = Double(totalPacketsReceived)
            self.currentUsage.timestamp = Date()

            // Limit history size
            if self.bandwidthHistory.count > 60 {
                self.bandwidthHistory.removeFirst()
            }
        }
    }

    /// Get network statistics for a specific interface
    /// - Parameter interface: Interface name
    /// - Returns: NetworkInterfaceStats or nil if interface not found
    private func getNetworkStats(for interface: String) -> NetworkInterfaceStats? {
        // In a real implementation, this would use system calls to get network stats
        // For this demo, we'll simulate network activity
        
        let baseBytes = Int64.random(in: 1000000...10000000)
        let basePackets = Int64.random(in: 1000...10000)

        return NetworkInterfaceStats(
            interface: interface,
            bytesIn: baseBytes,
            bytesOut: baseBytes,
            packetsIn: basePackets,
            packetsOut: basePackets,
            errorsIn: 0,
            errorsOut: 0,
            dropsIn: 0,
            dropsOut: 0
        )
    }

    /// Analyze usage patterns
    /// - Returns: Array of usage patterns
    private func analyzeUsagePatterns() -> [UsagePattern] {
        var patterns: [UsagePattern] = []

        // Analyze by time periods
        if bandwidthHistory.count >= 10 {
            // Calculate average usage
            var totalBytes: Int64 = 0
            for sample in bandwidthHistory {
                totalBytes += sample.bytesSent + sample.bytesReceived
            }
            let averageBytes = Double(totalBytes) / Double(bandwidthHistory.count)

            // Detect high usage periods
            var highUsagePeriods: [Date] = []
            for sample in bandwidthHistory {
                let totalBytes = sample.bytesSent + sample.bytesReceived
                if Double(totalBytes) > averageBytes * 1.5 {
                    highUsagePeriods.append(sample.timestamp)
                }
            }

            if !highUsagePeriods.isEmpty {
                patterns.append(UsagePattern(
                    type: .highUsage,
                    description: "High usage detected in \(highUsagePeriods.count) periods",
                    details: ["Average usage": "\(String(format: "%.2f", averageBytes)) bytes",
                             "High usage threshold": "\(String(format: "%.2f", averageBytes * 1.5)) bytes"]
                ))
            }
        }

        // Analyze protocol distribution (simulated)
        patterns.append(UsagePattern(
            type: .protocolDistribution,
            description: "Protocol usage distribution",
            details: ["TCP": "60%", "UDP": "30%", "ICMP": "10%"]
        ))

        return patterns
    }

    /// Update monitoring status on main thread
    /// - Parameter monitoring: Monitoring status
    private func updateMonitoringStatus(monitoring: Bool) {
        DispatchQueue.main.async { [weak self] in
            self?.isMonitoring = monitoring
            self?.monitoringStatus = monitoring ? "Monitoring bandwidth" : "Not monitoring"
        }
    }

    /// Handle errors and update error message
    /// - Parameter error: Error to handle
    private func handleError(_ error: Error) {
        DispatchQueue.main.async { [weak self] in
            if let bandwidthError = error as? BandwidthMonitorError {
                self?.errorMessage = bandwidthError.localizedDescription
            } else {
                self?.errorMessage = error.localizedDescription
            }
            self?.isMonitoring = false
            self?.monitoringStatus = "Monitoring failed"
        }
    }

    // MARK: - Error Handling

    /// BandwidthMonitor-specific errors
    public enum BandwidthMonitorError: Error {
        case notMonitoring
        case monitoringFailed(String)
        case invalidInterface(String)
        case permissionDenied
        case unknownError

        public var localizedDescription: String {
            switch self {
            case .notMonitoring:
                return "Bandwidth monitoring is not active"
            case .monitoringFailed(let message):
                return "Monitoring failed: \(message)"
            case .invalidInterface(let interface):
                return "Invalid network interface: \(interface)"
            case .permissionDenied:
                return "Permission denied for network monitoring"
            case .unknownError:
                return "Unknown bandwidth monitoring error"
            }
        }
    }
}

// MARK: - Supporting Types

/// BandwidthSample represents a single bandwidth measurement
@available(macOS 13.0, *)
public struct BandwidthSample: Identifiable {
    public let id = UUID()
    public let timestamp: Date
    public var bytesSent: Int64
    public var bytesReceived: Int64
    public var packetsSent: Int64
    public var packetsReceived: Int64
    public var interfaceStats: [String: InterfaceBandwidthSample]

    public init(timestamp: Date) {
        self.timestamp = timestamp
        self.bytesSent = 0
        self.bytesReceived = 0
        self.packetsSent = 0
        self.packetsReceived = 0
        self.interfaceStats = [:]
    }
}

/// InterfaceBandwidthSample represents bandwidth usage for a specific interface
@available(macOS 13.0, *)
public struct InterfaceBandwidthSample {
    public let interface: String
    public let bytesSent: Int64
    public let bytesReceived: Int64
    public let packetsSent: Int64
    public let packetsReceived: Int64

    public init(interface: String, bytesSent: Int64, bytesReceived: Int64, packetsSent: Int64, packetsReceived: Int64) {
        self.interface = interface
        self.bytesSent = bytesSent
        self.bytesReceived = bytesReceived
        self.packetsSent = packetsSent
        self.packetsReceived = packetsReceived
    }
}

/// BandwidthUsage represents current bandwidth usage
@available(macOS 13.0, *)
public struct BandwidthUsage {
    public var bytesSent: Double = 0
    public var bytesReceived: Double = 0
    public var packetsSent: Double = 0
    public var packetsReceived: Double = 0
    public var timestamp: Date = Date()

    public init() {}

    public init(bytesSent: Double, bytesReceived: Double, packetsSent: Double, packetsReceived: Double, timestamp: Date) {
        self.bytesSent = bytesSent
        self.bytesReceived = bytesReceived
        self.packetsSent = packetsSent
        self.packetsReceived = packetsReceived
        self.timestamp = timestamp
    }
}

/// BandwidthSummary contains aggregated bandwidth statistics
@available(macOS 13.0, *)
public struct BandwidthSummary {
    public var startTime: Date = Date()
    public var endTime: Date = Date()
    public var duration: TimeInterval = 0
    public var totalBytesSent: Int64 = 0
    public var totalBytesReceived: Int64 = 0
    public var totalPacketsSent: Int64 = 0
    public var totalPacketsReceived: Int64 = 0
    public var averageBytesSent: Double = 0
    public var averageBytesReceived: Double = 0
    public var averagePacketsSent: Double = 0
    public var averagePacketsReceived: Double = 0
    public var peakBytesSent: Int64 = 0
    public var peakBytesReceived: Int64 = 0
    public var peakPacketsSent: Int64 = 0
    public var peakPacketsReceived: Int64 = 0

    public init() {}
}

/// BandwidthReport contains detailed bandwidth analysis
@available(macOS 13.0, *)
public struct BandwidthReport {
    public let summary: BandwidthSummary
    public var interfaceStats: [String: InterfaceBandwidthStats]
    public var usagePatterns: [UsagePattern]

    public init(summary: BandwidthSummary) {
        self.summary = summary
        self.interfaceStats = [:]
        self.usagePatterns = []
    }
}

/// InterfaceBandwidthStats contains statistics for a specific interface
@available(macOS 13.0, *)
public struct InterfaceBandwidthStats {
    public let interface: String
    public var totalBytesSent: Int64 = 0
    public var totalBytesReceived: Int64 = 0
    public var totalPacketsSent: Int64 = 0
    public var totalPacketsReceived: Int64 = 0

    public init(interface: String) {
        self.interface = interface
    }
}

/// UsagePattern represents detected usage patterns
@available(macOS 13.0, *)
public struct UsagePattern {
    public let type: UsagePatternType
    public let description: String
    public let details: [String: String]

    public init(type: UsagePatternType, description: String, details: [String : String]) {
        self.type = type
        self.description = description
        self.details = details
    }
}

/// UsagePatternType defines types of usage patterns
@available(macOS 13.0, *)
public enum UsagePatternType {
    case highUsage
    case lowUsage
    case periodic
    case protocolDistribution
    case anomaly
}

/// NetworkInterfaceStats represents raw network interface statistics
private struct NetworkInterfaceStats {
    let interface: String
    let bytesIn: Int64
    let bytesOut: Int64
    let packetsIn: Int64
    let packetsOut: Int64
    let errorsIn: Int64
    let errorsOut: Int64
    let dropsIn: Int64
    let dropsOut: Int64

    init(interface: String, bytesIn: Int64, bytesOut: Int64, packetsIn: Int64, packetsOut: Int64, errorsIn: Int64, errorsOut: Int64, dropsIn: Int64, dropsOut: Int64) {
        self.interface = interface
        self.bytesIn = bytesIn
        self.bytesOut = bytesOut
        self.packetsIn = packetsIn
        self.packetsOut = packetsOut
        self.errorsIn = errorsIn
        self.errorsOut = errorsOut
        self.dropsIn = dropsIn
        self.dropsOut = dropsOut
    }
}