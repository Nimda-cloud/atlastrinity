//  SSHManager.swift
//  NetworkManager
//
//  Created by AtlasTrinity on 2024-01-01.
//  Copyright © 2024 AtlasTrinity. All rights reserved.

import Foundation
import Security
import Dispatch

/// SSHManager provides secure SSH communication using NMSSH framework
/// with public/private key generation and macOS Keychain storage
@available(macOS 13.0, *)
public class SSHManager: NSObject {

    // MARK: - Properties

    /// Connection status
    @Published public var isConnected: Bool = false
    
    /// Connection status message
    @Published public var connectionStatus: String = "Disconnected"
    
    /// Output from SSH session
    @Published public var output: String = ""
    
    /// Error messages
    @Published public var errorMessage: String = ""
    
    /// SSH session
    private var session: NMSSHSession?
    
    /// Dispatch queue for thread safety
    private let sshQueue = DispatchQueue(label: "com.atlastrinity.ssh", attributes: .concurrent)
    
    /// Keychain service name
    private let keychainService = "com.atlastrinity.ssh"

    // MARK: - Initialization

    public override init() {
        super.init()
    }

    deinit {
        disconnect()
    }

    // MARK: - Key Management

    /// Generate RSA key pair and store in Keychain
    /// - Parameters:
    ///   - keyName: Name for the key pair
    ///   - keySize: Key size in bits (default: 4096)
    /// - Returns: Boolean indicating success
    /// - Throws: SSHError if key generation fails
    public func generateKeyPair(keyName: String, keySize: Int = 4096) throws -> Bool {
        return try sshQueue.sync(flags: .barrier) {
            // Check if key already exists
            if keyExistsInKeychain(keyName: keyName) {
                throw SSHError.keyAlreadyExists
            }

            // Generate RSA key pair
            let attributes: [String: Any] = [
                kSecAttrKeyType as String: kSecAttrKeyTypeRSA,
                kSecAttrKeySizeInBits as String: keySize,
                kSecPrivateKeyAttrs as String: [
                    kSecAttrIsPermanent as String: true,
                    kSecAttrApplicationTag as String: "com.atlastrinity.ssh.private.\\(keyName)".data(using: .utf8)!,
                    kSecAttrLabel as String: "AtlasTrinity SSH Private Key - \\(keyName)"
                ],
                kSecPublicKeyAttrs as String: [
                    kSecAttrIsPermanent as String: true,
                    kSecAttrApplicationTag as String: "com.atlastrinity.ssh.public.\\(keyName)".data(using: .utf8)!,
                    kSecAttrLabel as String: "AtlasTrinity SSH Public Key - \\(keyName)"
                ]
            ]

            var error: Unmanaged<CFError>?
            guard let privateKey = SecKeyCreateRandomKey(attributes as CFDictionary, &error) else {
                if let error = error?.takeRetainedValue() {
                    throw SSHError.keyGenerationFailed(error.localizedDescription)
                }
                throw SSHError.keyGenerationFailed("Unknown error")
            }

            // Store in Keychain
            let addQuery: [String: Any] = [
                kSecClass as String: kSecClassKey,
                kSecAttrApplicationTag as String: "com.atlastrinity.ssh.private.\\(keyName)".data(using: .utf8)!,
                kSecAttrKeyType as String: kSecAttrKeyTypeRSA,
                kSecAttrLabel as String: "AtlasTrinity SSH Private Key - \\(keyName)",
                kSecValueRef as String: privateKey,
                kSecReturnData as String: false
            ]

            let status = SecItemAdd(addQuery as CFDictionary, nil)
            guard status == errSecSuccess else {
                throw SSHError.keychainError("Failed to store private key: \\(status)")
            }

            return true
        }
    }

    /// Check if key exists in Keychain
    /// - Parameter keyName: Name of the key to check
    /// - Returns: Boolean indicating if key exists
    public func keyExistsInKeychain(keyName: String) -> Bool {
        return sshQueue.sync {
            let query: [String: Any] = [
                kSecClass as String: kSecClassKey,
                kSecAttrApplicationTag as String: "com.atlastrinity.ssh.private.\\(keyName)".data(using: .utf8)!,
                kSecReturnAttributes as String: true
            ]

            var item: CFTypeRef?
            let status = SecItemCopyMatching(query as CFDictionary, &item)
            return status == errSecSuccess
        }
    }

    /// Get private key from Keychain
    /// - Parameter keyName: Name of the key to retrieve
    /// - Returns: SecKey object
    /// - Throws: SSHError if key retrieval fails
    public func getPrivateKeyFromKeychain(keyName: String) throws -> SecKey {
        return try sshQueue.sync {
            let query: [String: Any] = [
                kSecClass as String: kSecClassKey,
                kSecAttrApplicationTag as String: "com.atlastrinity.ssh.private.\\(keyName)".data(using: .utf8)!,
                kSecAttrKeyType as String: kSecAttrKeyTypeRSA,
                kSecReturnRef as String: true
            ]

            var item: CFTypeRef?
            let status = SecItemCopyMatching(query as CFDictionary, &item)
            
            guard status == errSecSuccess else {
                throw SSHError.keychainError("Failed to retrieve private key: \\(status)")
            }

            guard let key = item as? SecKey else {
                throw SSHError.keychainError("Retrieved item is not a valid key")
            }

            return key
        }
    }

    /// Get public key from Keychain
    /// - Parameter keyName: Name of the key to retrieve
    /// - Returns: SecKey object
    /// - Throws: SSHError if key retrieval fails
    public func getPublicKeyFromKeychain(keyName: String) throws -> SecKey {
        return try sshQueue.sync {
            let query: [String: Any] = [
                kSecClass as String: kSecClassKey,
                kSecAttrApplicationTag as String: "com.atlastrinity.ssh.public.\\(keyName)".data(using: .utf8)!,
                kSecAttrKeyType as String: kSecAttrKeyTypeRSA,
                kSecReturnRef as String: true
            ]

            var item: CFTypeRef?
            let status = SecItemCopyMatching(query as CFDictionary, &item)
            
            guard status == errSecSuccess else {
                throw SSHError.keychainError("Failed to retrieve public key: \\(status)")
            }

            guard let key = item as? SecKey else {
                throw SSHError.keychainError("Retrieved item is not a valid key")
            }

            return key
        }
    }

    /// Delete key pair from Keychain
    /// - Parameter keyName: Name of the key pair to delete
    /// - Returns: Boolean indicating success
    /// - Throws: SSHError if deletion fails
    public func deleteKeyPairFromKeychain(keyName: String) throws -> Bool {
        return try sshQueue.sync(flags: .barrier) {
            // Delete private key
            let privateQuery: [String: Any] = [
                kSecClass as String: kSecClassKey,
                kSecAttrApplicationTag as String: "com.atlastrinity.ssh.private.\\(keyName)".data(using: .utf8)!,
                kSecAttrKeyType as String: kSecAttrKeyTypeRSA
            ]

            let privateStatus = SecItemDelete(privateQuery as CFDictionary)
            
            // Delete public key
            let publicQuery: [String: Any] = [
                kSecClass as String: kSecClassKey,
                kSecAttrApplicationTag as String: "com.atlastrinity.ssh.public.\\(keyName)".data(using: .utf8)!,
                kSecAttrKeyType as String: kSecAttrKeyTypeRSA
            ]

            let publicStatus = SecItemDelete(publicQuery as CFDictionary)
            
            return privateStatus == errSecSuccess && publicStatus == errSecSuccess
        }
    }

    // MARK: - SSH Connection Management

    /// Connect to SSH server using key-based authentication
    /// - Parameters:
    ///   - host: Hostname or IP address
    ///   - port: Port number (default: 22)
    ///   - username: Username for authentication
    ///   - keyName: Name of the key pair in Keychain
    ///   - timeout: Connection timeout in seconds (default: 30)
    public func connectWithKey(
        host: String,
        port: Int = 22,
        username: String,
        keyName: String,
        timeout: TimeInterval = 30.0
    ) {
        sshQueue.async(flags: .barrier) { [weak self] in
            guard let self = self else { return }
            
            self.disconnect()
            
            do {
                // Get private key from Keychain
                let privateKey = try self.getPrivateKeyFromKeychain(keyName: keyName)
                
                // Create SSH session
                let session = NMSSHSession.connect(toHost: host, withUsername: username)
                session?.connectTimeout = timeout
                
                // Configure key-based authentication
                session?.authenticate(byInMemoryPrivateKey: privateKey)
                
                // Connect
                session?.connect()
                
                if session?.isConnected == true {
                    self.session = session
                    self.updateConnectionStatus(connected: true, host: host)
                    self.startSessionMonitoring()
                } else {
                    throw SSHError.connectionFailed("Failed to establish SSH connection")
                }
                
            } catch {
                self.handleError(error)
            }
        }
    }

    /// Connect to SSH server using password authentication
    /// - Parameters:
    ///   - host: Hostname or IP address
    ///   - port: Port number (default: 22)
    ///   - username: Username for authentication
    ///   - password: Password for authentication
    ///   - timeout: Connection timeout in seconds (default: 30)
    public func connectWithPassword(
        host: String,
        port: Int = 22,
        username: String,
        password: String,
        timeout: TimeInterval = 30.0
    ) {
        sshQueue.async(flags: .barrier) { [weak self] in
            guard let self = self else { return }
            
            self.disconnect()
            
            do {
                // Create SSH session
                let session = NMSSHSession.connect(toHost: host, withUsername: username)
                session?.connectTimeout = timeout
                
                // Configure password authentication
                session?.authenticate(byPassword: password)
                
                // Connect
                session?.connect()
                
                if session?.isConnected == true {
                    self.session = session
                    self.updateConnectionStatus(connected: true, host: host)
                    self.startSessionMonitoring()
                } else {
                    throw SSHError.connectionFailed("Failed to establish SSH connection")
                }
                
            } catch {
                self.handleError(error)
            }
        }
    }

    /// Disconnect from SSH server
    public func disconnect() {
        sshQueue.async(flags: .barrier) { [weak self] in
            guard let self = self else { return }
            
            self.session?.disconnect()
            self.session = nil
            self.updateConnectionStatus(connected: false, host: nil)
        }
    }

    /// Execute command on SSH server
    /// - Parameters:
    ///   - command: Command to execute
    ///   - timeout: Command execution timeout in seconds (default: 60)
    ///   - completion: Completion handler with result
    public func executeCommand(
        _ command: String,
        timeout: TimeInterval = 60.0,
        completion: @escaping (Result<String, Error>) -> Void
    ) {
        sshQueue.async { [weak self] in
            guard let self = self else {
                completion(.failure(SSHError.notConnected))
                return
            }
            
            guard let session = self.session, session.isConnected else {
                completion(.failure(SSHError.notConnected))
                return
            }
            
            do {
                let result = try session.channel.execute(command, timeout: timeout)
                completion(.success(result))
            } catch {
                completion(.failure(error))
            }
        }
    }

    // MARK: - Private Methods

    /// Update connection status on main thread
    /// - Parameters:
    ///   - connected: Connection status
    ///   - host: Host name (optional)
    private func updateConnectionStatus(connected: Bool, host: String?) {
        DispatchQueue.main.async { [weak self] in
            self?.isConnected = connected
            if connected, let host = host {
                self?.connectionStatus = "Connected to \\(host)"
            } else {
                self?.connectionStatus = "Disconnected"
            }
        }
    }

    /// Handle errors and update error message
    /// - Parameter error: Error to handle
    private func handleError(_ error: Error) {
        DispatchQueue.main.async { [weak self] in
            if let sshError = error as? SSHError {
                self?.errorMessage = sshError.localizedDescription
            } else {
                self?.errorMessage = error.localizedDescription
            }
            self?.isConnected = false
            self?.connectionStatus = "Connection failed"
        }
    }

    /// Start session monitoring
    private func startSessionMonitoring() {
        // Implement session monitoring logic
    }

    // MARK: - Error Handling

    /// SSH-specific errors
    public enum SSHError: Error {
        case notConnected
        case connectionFailed(String)
        case authenticationFailed(String)
        case keyGenerationFailed(String)
        case keyAlreadyExists
        case keychainError(String)
        case invalidKey
        case sessionError(String)
        case unknownError

        public var localizedDescription: String {
            switch self {
            case .notConnected:
                return "Not connected to SSH server"
            case .connectionFailed(let message):
                return "Connection failed: \\(message)"
            case .authenticationFailed(let message):
                return "Authentication failed: \\(message)"
            case .keyGenerationFailed(let message):
                return "Key generation failed: \\(message)"
            case .keyAlreadyExists:
                return "Key already exists in Keychain"
            case .keychainError(let message):
                return "Keychain error: \\(message)"
            case .invalidKey:
                return "Invalid SSH key"
            case .sessionError(let message):
                return "Session error: \\(message)"
            case .unknownError:
                return "Unknown SSH error"
            }
        }
    }
}