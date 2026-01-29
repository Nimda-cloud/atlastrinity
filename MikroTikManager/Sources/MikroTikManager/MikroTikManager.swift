import Foundation
import Network
import SwiftUI

// MARK: - SSH Manager
@MainActor
class SSHManager: ObservableObject {
    @Published var isConnected = false
    @Published var connectionStatus = "Disconnected"
    @Published var output = ""
    @Published var errorMessage = ""

    private var task: Process?
    private var outputPipe: Pipe?
    private var errorPipe: Pipe?
    private var timer: Timer?

    func connect(host: String, port: Int, username: String, password: String) {
        disconnect()

        let command =
            "sshpass -p '" + password + "' ssh -o StrictHostKeyChecking=no " + username + "@" + host
            + " -p " + String(port)

        task = Process()
        task?.executableURL = URL(fileURLWithPath: "/bin/bash")
        task?.arguments = ["-c", command]

        outputPipe = Pipe()
        errorPipe = Pipe()

        task?.standardOutput = outputPipe
        task?.standardError = errorPipe

        let outputHandler = outputPipe?.fileHandleForReading
        let errorHandler = errorPipe?.fileHandleForReading

        outputHandler?.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if let string = String(data: data, encoding: .utf8) {
                Task { @MainActor in
                    self?.output += string
                }
            }
        }

        errorHandler?.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if let string = String(data: data, encoding: .utf8) {
                Task { @MainActor in
                    self?.errorMessage += string
                }
            }
        }

        do {
            try task?.run()
            self.isConnected = true
            self.connectionStatus = "Connected to " + host

            // Start reconnection timer
            self.startReconnectionTimer(
                host: host, port: port, username: username, password: password)
        } catch {
            self.errorMessage = "Failed to start SSH: " + error.localizedDescription
            self.isConnected = false
            self.connectionStatus = "Connection failed"
        }
    }

    func disconnect() {
        timer?.invalidate()
        timer = nil

        task?.terminate()
        task = nil

        outputPipe?.fileHandleForReading.readabilityHandler = nil
        errorPipe?.fileHandleForReading.readabilityHandler = nil

        self.isConnected = false
        self.connectionStatus = "Disconnected"
    }

    func sendCommand(_ command: String) {
        guard isConnected else {
            errorMessage = "Not connected to any device"
            return
        }

        let input = command + "\n"
        if let inputData = input.data(using: .utf8),
            let standardInput = task?.standardInput as? Pipe
        {
            standardInput.fileHandleForWriting.write(inputData)
        }
    }

    private func startReconnectionTimer(host: String, port: Int, username: String, password: String)
    {
        timer = Timer.scheduledTimer(withTimeInterval: 30.0, repeats: true) { [weak self] _ in
            guard let self = self else { return }

            // Check if connection is still alive by sending a simple command
            Task { @MainActor in
                self.sendCommand("echo ping")
            }

            // If we haven't received output in a while, reconnect
            DispatchQueue.main.asyncAfter(deadline: .now() + 5.0) {
                Task { @MainActor in
                    if self.output.contains("ping") {
                        // Connection is alive
                    } else {
                        // Attempt to reconnect
                        self.disconnect()
                        self.connect(host: host, port: port, username: username, password: password)
                    }
                }
            }
        }
    }
}

// MARK: - Device Model
struct Device: Identifiable, Codable {
    var id = UUID()
    var name: String
    var host: String
    var port: Int
    var username: String
    var password: String
    var isFavorite: Bool

    static func sampleDevices() -> [Device] {
        return [
            Device(
                name: "RouterOS 1", host: "192.168.88.1", port: 22, username: "admin", password: "",
                isFavorite: true),
            Device(
                name: "RouterOS 2", host: "192.168.1.1", port: 22, username: "admin", password: "",
                isFavorite: false),
            Device(
                name: "Switch", host: "192.168.88.2", port: 22, username: "admin", password: "",
                isFavorite: false),
        ]
    }
}

// MARK: - Dashboard View
struct DashboardView: View {
    @StateObject private var sshManager = SSHManager()
    @State private var devices: [Device] = Device.sampleDevices()
    @State private var selectedDevice: Device?
    @State private var showingAddDevice = false
    @State private var newDevice = Device(
        name: "", host: "", port: 22, username: "admin", password: "", isFavorite: false)
    @State private var commandInput = ""

    var body: some View {
        NavigationView {
            List {
                Section(header: Text("Favorites")) {
                    ForEach(devices.filter { $0.isFavorite }) { device in
                        deviceRow(device: device)
                    }
                }

                Section(header: Text("All Devices")) {
                    ForEach(devices.filter { !$0.isFavorite }) { device in
                        deviceRow(device: device)
                    }
                }
            }
            .listStyle(SidebarListStyle())
            .navigationTitle("MikroTik Manager")
            .toolbar {
                ToolbarItem(placement: .navigation) {
                    Button(action: { showingAddDevice = true }) {
                        Image(systemName: "plus")
                    }
                }
            }

            if let selectedDevice = selectedDevice {
                DeviceDetailView(
                    device: selectedDevice, sshManager: sshManager, commandInput: $commandInput
                )
                .frame(minWidth: 400)
            } else {
                Text("Select a device to manage")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .sheet(isPresented: $showingAddDevice) {
            AddDeviceView(newDevice: $newDevice, devices: $devices)
        }
    }

    private func deviceRow(device: Device) -> some View {
        HStack {
            Image(systemName: device.isFavorite ? "star.fill" : "star")
                .foregroundColor(device.isFavorite ? .yellow : .gray)

            VStack(alignment: .leading) {
                Text(device.name)
                    .font(.headline)
                Text(device.host)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            Spacer()

            if sshManager.isConnected && selectedDevice?.id == device.id {
                Circle()
                    .fill(Color.green)
                    .frame(width: 10, height: 10)
            }
        }
        .contentShape(Rectangle())
        .onTapGesture {
            selectedDevice = device
            sshManager.connect(
                host: device.host,
                port: device.port,
                username: device.username,
                password: device.password
            )
        }
    }
}

// MARK: - Device Detail View
struct DeviceDetailView: View {
    let device: Device
    @ObservedObject var sshManager: SSHManager
    @Binding var commandInput: String

    var body: some View {
        VStack(spacing: 0) {
            // Connection Status Bar
            HStack {
                Circle()
                    .fill(sshManager.isConnected ? Color.green : Color.red)
                    .frame(width: 12, height: 12)

                Text(sshManager.connectionStatus)
                    .font(.subheadline)
                    .foregroundColor(sshManager.isConnected ? .green : .red)

                Spacer()

                Button(action: {
                    sshManager.disconnect()
                }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.red)
                }
                .disabled(!sshManager.isConnected)
            }
            .padding()
            .background(Color.secondary.opacity(0.1))

            // Output Console
            ScrollView {
                ScrollViewReader { scrollView in
                    Text(sshManager.output)
                        .font(.system(.body, design: .monospaced))
                        .textSelection(.enabled)
                        .padding()
                        .onChange(of: sshManager.output) { _ in
                            scrollView.scrollTo("bottom", anchor: .bottom)
                        }
                        .id("bottom")
                }
            }
            .background(Color.secondary.opacity(0.1))

            // Command Input
            HStack {
                TextField(
                    "Enter command...", text: $commandInput,
                    onCommit: {
                        if !commandInput.isEmpty {
                            sshManager.sendCommand(commandInput)
                            commandInput = ""
                        }
                    }
                )
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .disabled(!sshManager.isConnected)

                Button(action: {
                    if !commandInput.isEmpty {
                        sshManager.sendCommand(commandInput)
                        commandInput = ""
                    }
                }) {
                    Image(systemName: "arrow.right.circle.fill")
                        .foregroundColor(sshManager.isConnected ? .blue : .gray)
                }
                .disabled(!sshManager.isConnected || commandInput.isEmpty)
            }
            .padding()
            .background(Color(NSColor.windowBackgroundColor))

            // Error Display
            if !sshManager.errorMessage.isEmpty {
                Text("Error: " + sshManager.errorMessage)
                    .foregroundColor(.red)
                    .font(.caption)
                    .padding(.horizontal)
            }
        }
        .navigationTitle(device.name)
    }
}

// MARK: - Add Device View
struct AddDeviceView: View {
    @Binding var newDevice: Device
    @Binding var devices: [Device]
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Device Information")) {
                    TextField("Name", text: $newDevice.name)
                    TextField("Host/IP", text: $newDevice.host)
                    TextField("Port", value: $newDevice.port, formatter: NumberFormatter())
                    TextField("Username", text: $newDevice.username)
                    SecureField("Password", text: $newDevice.password)
                }

                Section {
                    Toggle("Add to Favorites", isOn: $newDevice.isFavorite)
                }
            }
            .navigationTitle("Add New Device")
            .toolbar {
                ToolbarItem(placement: .navigation) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        devices.append(newDevice)
                        newDevice = Device(
                            name: "", host: "", port: 22, username: "admin", password: "",
                            isFavorite: false)
                        dismiss()
                    }
                    .disabled(newDevice.name.isEmpty || newDevice.host.isEmpty)
                }
            }
        }
    }
}

// MARK: - Main App
@main
struct MikroTikManagerApp: App {
    var body: some Scene {
        WindowGroup {
            DashboardView()
                .frame(minWidth: 800, minHeight: 600)
        }
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(replacing: .newItem) {}
            CommandGroup(replacing: .saveItem) {}
        }
    }
}

// MARK: - Preview
struct DashboardView_Previews: PreviewProvider {
    static var previews: some View {
        DashboardView()
    }
}
