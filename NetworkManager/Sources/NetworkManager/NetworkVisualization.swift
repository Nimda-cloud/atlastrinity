//  NetworkVisualization.swift
//  NetworkManager
//
//  Created by AtlasTrinity on 2024-01-01.
//  Copyright © 2024 AtlasTrinity. All rights reserved.

import SwiftUI
import Charts

/// NetworkVisualization provides UI components for visualizing network data
@available(macOS 13.0, *)
public struct NetworkVisualization {

    // MARK: - Bandwidth Visualization

    /// Bandwidth usage chart view
    /// - Parameters:
    ///   - bandwidthHistory: Array of BandwidthSample objects
    ///   - title: Chart title
    ///   - showLegend: Whether to show legend
    /// - Returns: SwiftUI View displaying bandwidth usage chart
    public static func bandwidthChart(
        bandwidthHistory: [BandwidthSample],
        title: String = "Bandwidth Usage",
        showLegend: Bool = true
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .padding(.bottom, 4)

            if bandwidthHistory.isEmpty {
                Text("No bandwidth data available")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Chart {
                    // Bytes sent
                    ForEach(bandwidthHistory) { sample in
                        LineMark(
                            x: .value("Time", sample.timestamp),
                            y: .value("Sent", sample.bytesSent),
                            series: .value("Type", "Sent")
                        )
                        .foregroundStyle(.blue)
                        .interpolationMethod(.catmullRom)

                        // Bytes received
                        LineMark(
                            x: .value("Time", sample.timestamp),
                            y: .value("Received", sample.bytesReceived),
                            series: .value("Type", "Received")
                        )
                        .foregroundStyle(.green)
                        .interpolationMethod(.catmullRom)
                    }
                }
                .chartXAxis {
                    AxisMarks(values: .automatic) { value in
                        if let date = value.as(Date.self) {
                            AxisValueLabel(
                                format: .dateTime.hour().minute(),
                                centered: true
                            )
                        }
                    }
                }
                .chartYAxis {
                    AxisMarks(position: .leading)
                }
                .chartLegend(position: showLegend ? .bottom : .hidden, spacing: 12)
                .frame(height: 200)
            }
        }
        .padding()
        .background(Color(.windowBackgroundColor))
        .cornerRadius(8)
    }

    /// Protocol distribution pie chart
    /// - Parameters:
    ///   - protocolDistribution: Dictionary of protocol names to counts
    ///   - title: Chart title
    /// - Returns: SwiftUI View displaying protocol distribution
    public static func protocolDistributionChart(
        protocolDistribution: [String: Int],
        title: String = "Protocol Distribution"
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .padding(.bottom, 4)

            if protocolDistribution.isEmpty {
                Text("No protocol data available")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Chart {
                    ForEach(Array(protocolDistribution.sorted { $0.value > $1.value }), id: \.key) { protocol, count in
                        SectorMark(
                            angle: .value("Count", count),
                            innerRadius: .ratio(0.6),
                            angularInset: 1.5
                        )
                        .cornerRadius(4)
                        .foregroundStyle(by: .value("Protocol", protocol))
                        .annotation(position: .overlay) {
                            Text("\{count}")
                                .font(.caption)
                                .foregroundStyle(.white)
                        }
                    }
                }
                .chartLegend(position: .bottom, spacing: 12)
                .frame(height: 250)
            }
        }
        .padding()
        .background(Color(.windowBackgroundColor))
        .cornerRadius(8)
    }

    /// Packet statistics dashboard
    /// - Parameters:
    ///   - statistics: PacketStatistics object
    ///   - title: Dashboard title
    /// - Returns: SwiftUI View displaying packet statistics
    public static func packetStatisticsDashboard(
        statistics: PacketStatistics,
        title: String = "Packet Statistics"
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.headline)
                .padding(.bottom, 8)

            if statistics.totalPackets == 0 {
                Text("No packet statistics available")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 12) {
                    GridRow {
                        StatCard(
                            title: "Total Packets",
                            value: "\{statistics.totalPackets}",
                            color: .blue
                        )
                        StatCard(
                            title: "Total Bytes",
                            value: byteFormatter(bytes: statistics.totalBytes),
                            color: .green
                        )
                    }

                    GridRow {
                        StatCard(
                            title: "Duration",
                            value: statistics.startTime != nil && statistics.endTime != nil 
                                ? durationFormatter(duration: statistics.endTime!.timeIntervalSince(statistics.startTime!))
                                : "N/A",
                            color: .purple
                        )
                        StatCard(
                            title: "Protocols",
                            value: "\{statistics.protocolCounts.count}",
                            color: .orange
                        )
                    }

                    if !statistics.protocolCounts.isEmpty {
                        GridRow {
                            Text("Protocol Breakdown:")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                                .gridCellColumns(2)

                            VStack(alignment: .leading, spacing: 4) {
                                ForEach(Array(statistics.protocolCounts.sorted { $0.value > $1.value }).prefix(5), id: \.key) { protocol, count in
                                    HStack {
                                        Text(protocol)
                                            .frame(width: 80, alignment: .leading)
                                        Text("\{count}")
                                            .frame(width: 60, alignment: .trailing)
                                        ProgressView(value: Double(count), total: Double(statistics.totalPackets))
                                            .frame(width: 100)
                                    }
                                }
                            }
                            .gridCellColumns(2)
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(.windowBackgroundColor))
        .cornerRadius(8)
    }

    /// Bandwidth summary view
    /// - Parameters:
    ///   - summary: BandwidthSummary object
    ///   - title: View title
    /// - Returns: SwiftUI View displaying bandwidth summary
    public static func bandwidthSummaryView(
        summary: BandwidthSummary,
        title: String = "Bandwidth Summary"
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.headline)
                .padding(.bottom, 8)

            if summary.totalBytesSent == 0 && summary.totalBytesReceived == 0 {
                Text("No bandwidth summary available")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 12) {
                    GridRow {
                        StatCard(
                            title: "Total Sent",
                            value: byteFormatter(bytes: summary.totalBytesSent),
                            color: .blue
                        )
                        StatCard(
                            title: "Total Received",
                            value: byteFormatter(bytes: summary.totalBytesReceived),
                            color: .green
                        )
                    }

                    GridRow {
                        StatCard(
                            title: "Peak Sent",
                            value: byteFormatter(bytes: summary.peakBytesSent),
                            color: .red
                        )
                        StatCard(
                            title: "Peak Received",
                            value: byteFormatter(bytes: summary.peakBytesReceived),
                            color: .orange
                        )
                    }

                    GridRow {
                        StatCard(
                            title: "Avg Sent",
                            value: byteFormatter(bytes: Int64(summary.averageBytesSent)),
                            color: .blue
                        )
                        StatCard(
                            title: "Avg Received",
                            value: byteFormatter(bytes: Int64(summary.averageBytesReceived)),
                            color: .green
                        )
                    }

                    if summary.duration > 0 {
                        GridRow {
                            StatCard(
                                title: "Duration",
                                value: durationFormatter(duration: summary.duration),
                                color: .purple
                            )
                            StatCard(
                                title: "Start Time",
                                value: dateFormatter(date: summary.startTime),
                                color: .secondary
                            )
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(.windowBackgroundColor))
        .cornerRadius(8)
    }

    // MARK: - Helper Components

    /// Stat card component for displaying key metrics
    private static func StatCard(title: String, value: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
            Text(value)
                .font(.title3)
                .fontWeight(.semibold)
                .foregroundColor(color)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.controlBackgroundColor))
        .cornerRadius(6)
    }

    // MARK: - Formatters

    /// Format bytes to human-readable string
    /// - Parameter bytes: Number of bytes
    /// - Returns: Formatted string (e.g., "1.2 MB")
    private static func byteFormatter(bytes: Int64) -> String {
        let formatter = ByteCountFormatter()
        formatter.allowedUnits = [.useMB, .useGB]
        formatter.countStyle = .decimal
        formatter.includesUnit = true
        return formatter.string(fromByteCount: bytes)
    }

    /// Format duration to human-readable string
    /// - Parameter duration: Duration in seconds
    /// - Returns: Formatted string (e.g., "5m 30s")
    private static func durationFormatter(duration: TimeInterval) -> String {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = [.hour, .minute, .second]
        formatter.unitsStyle = .abbreviated
        formatter.zeroFormattingBehavior = .dropAll
        return formatter.string(from: duration) ?? "\{duration)s"
    }

    /// Format date to human-readable string
    /// - Parameter date: Date to format
    /// - Returns: Formatted string
    private static func dateFormatter(date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    // MARK: - Packet Detail View

    /// Packet detail view for displaying individual packet information
    /// - Parameters:
    ///   - packet: NetworkPacket to display
    ///   - showRawData: Whether to show raw packet data
    /// - Returns: SwiftUI View displaying packet details
    public static func packetDetailView(
        packet: NetworkPacket,
        showRawData: Bool = false
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                Text("Packet Details")
                    .font(.headline)
                Spacer()
                Text(dateFormatter(date: packet.timestamp))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Divider()

            // Basic info
            Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 8) {
                GridRow {
                    Text("Source:")
                        .foregroundColor(.secondary)
                    Text("\{packet.sourceIP ?? "N/A"}:\{packet.sourcePort?.description ?? "N/A"}")
                }

                GridRow {
                    Text("Destination:")
                        .foregroundColor(.secondary)
                    Text("\{packet.destinationIP ?? "N/A"}:\{packet.destinationPort?.description ?? "N/A"}")
                }

                GridRow {
                    Text("Protocol:")
                        .foregroundColor(.secondary)
                    Text(packet.protocol ?? "Unknown")
                        .fontWeight(.semibold)
                }

                GridRow {
                    Text("Length:")
                        .foregroundColor(.secondary)
                    Text("\{packet.length} bytes")
                }

                GridRow {
                    Text("Interface:")
                        .foregroundColor(.secondary)
                    Text(packet.interface)
                }
            }

            if showRawData, let rawData = packet.rawData, !rawData.isEmpty {
                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    Text("Raw Data (\{rawData.count} bytes)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    ScrollView(.horizontal) {
                        Text(rawData.hexEncodedString())
                            .font(.system(.caption, design: .monospaced))
                            .textSelection(.enabled)
                    }
                    .frame(height: 60)
                }
            }
        }
        .padding()
        .background(Color(.windowBackgroundColor))
        .cornerRadius(8)
    }

    // MARK: - Usage Patterns View

    /// Usage patterns view for displaying detected patterns
    /// - Parameters:
    ///   - patterns: Array of UsagePattern objects
    ///   - title: View title
    /// - Returns: SwiftUI View displaying usage patterns
    public static func usagePatternsView(
        patterns: [UsagePattern],
        title: String = "Usage Patterns"
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.headline)
                .padding(.bottom, 8)

            if patterns.isEmpty {
                Text("No usage patterns detected")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ForEach(patterns, id: \.description) { pattern in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            patternIcon(for: pattern.type)
                            Text(pattern.description)
                                .font(.subheadline)
                                .fontWeight(.medium)
                            Spacer()
                        }

                        ForEach(Array(pattern.details.sorted { $0.key < $1.key }), id: \.key) { key, value in
                            HStack {
                                Text(key)
                                    .frame(width: 120, alignment: .leading)
                                    .foregroundColor(.secondary)
                                Text(value)
                                    .frame(alignment: .leading)
                            }
                        }
                    }
                    .padding()
                    .background(Color(.controlBackgroundColor))
                    .cornerRadius(6)
                }
            }
        }
        .padding()
        .background(Color(.windowBackgroundColor))
        .cornerRadius(8)
    }

    // MARK: - Helper Methods

    /// Get icon for usage pattern type
    /// - Parameter type: UsagePatternType
    /// - Returns: SwiftUI Image
    private static func patternIcon(for type: UsagePatternType) -> some View {
        switch type {
        case .highUsage:
            return Image(systemName: "arrow.up.circle.fill")
                .foregroundColor(.red)
        case .lowUsage:
            return Image(systemName: "arrow.down.circle.fill")
                .foregroundColor(.green)
        case .periodic:
            return Image(systemName: "clock.arrow.circlepath")
                .foregroundColor(.blue)
        case .protocolDistribution:
            return Image(systemName: "network")
                .foregroundColor(.purple)
        case .anomaly:
            return Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(.orange)
        }
    }
}

// MARK: - Data Extension for Hex Encoding

extension Data {
    func hexEncodedString() -> String {
        return map { String(format: "%02hhx", $0) }.joined()
    }
}