//  SSHManagerTests.swift
//  NetworkManagerTests
//
//  Created by AtlasTrinity on 2024-01-01.
//  Copyright © 2024 AtlasTrinity. All rights reserved.

import XCTest
@testable import NetworkManager

@available(macOS 13.0, *)
final class SSHManagerTests: XCTestCase {

    var sshManager: SSHManager!
    
    override func setUp() {
        super.setUp()
        sshManager = SSHManager()
    }
    
    override func tearDown() {
        sshManager = nil
        super.tearDown()
    }

    func testKeyGenerationAndStorage() {
        let expectation = XCTestExpectation(description: "Key generation and storage")
        
        DispatchQueue.global().async {
            do {
                // Test key generation
                let keyName = "test_key_\\(UUID().uuidString)"
                
                // Verify key doesn't exist initially
                let existsBefore = self.sshManager.keyExistsInKeychain(keyName: keyName)
                XCTAssertFalse(existsBefore, "Key should not exist before generation")
                
                // Generate key
                let success = try self.sshManager.generateKeyPair(keyName: keyName, keySize: 2048)
                XCTAssertTrue(success, "Key generation should succeed")
                
                // Verify key exists after generation
                let existsAfter = self.sshManager.keyExistsInKeychain(keyName: keyName)
                XCTAssertTrue(existsAfter, "Key should exist after generation")
                
                // Test key retrieval
                let privateKey = try self.sshManager.getPrivateKeyFromKeychain(keyName: keyName)
                XCTAssertNotNil(privateKey, "Private key should be retrievable")
                
                let publicKey = try self.sshManager.getPublicKeyFromKeychain(keyName: keyName)
                XCTAssertNotNil(publicKey, "Public key should be retrievable")
                
                // Test key deletion
                let deleteSuccess = try self.sshManager.deleteKeyPairFromKeychain(keyName: keyName)
                XCTAssertTrue(deleteSuccess, "Key deletion should succeed")
                
                // Verify key doesn't exist after deletion
                let existsAfterDeletion = self.sshManager.keyExistsInKeychain(keyName: keyName)
                XCTAssertFalse(existsAfterDeletion, "Key should not exist after deletion")
                
                expectation.fulfill()
                
            } catch {
                XCTFail("Key management test failed: \\(error.localizedDescription)")
                expectation.fulfill()
            }
        }
        
        wait(for: [expectation], timeout: 10.0)
    }

    func testDuplicateKeyGeneration() {
        let expectation = XCTestExpectation(description: "Duplicate key generation")
        
        DispatchQueue.global().async {
            do {
                let keyName = "duplicate_test_key_\\(UUID().uuidString)"
                
                // Generate first key
                _ = try self.sshManager.generateKeyPair(keyName: keyName)
                
                // Try to generate duplicate key - should throw error
                XCTAssertThrowsError(try self.sshManager.generateKeyPair(keyName: keyName)) { error in
                    if let sshError = error as? SSHManager.SSHError {
                        XCTAssertEqual(sshError, SSHManager.SSHError.keyAlreadyExists)
                    } else {
                        XCTFail("Expected SSHError.keyAlreadyExists, got \\(error)")
                    }
                }
                
                // Clean up
                _ = try self.sshManager.deleteKeyPairFromKeychain(keyName: keyName)
                
                expectation.fulfill()
                
            } catch {
                XCTFail("Duplicate key test failed: \\(error.localizedDescription)")
                expectation.fulfill()
            }
        }
        
        wait(for: [expectation], timeout: 10.0)
    }

    func testInvalidKeyRetrieval() {
        let expectation = XCTestExpectation(description: "Invalid key retrieval")
        
        DispatchQueue.global().async {
            do {
                let nonExistentKeyName = "non_existent_key_\\(UUID().uuidString)"
                
                // Try to retrieve non-existent private key
                XCTAssertThrowsError(try self.sshManager.getPrivateKeyFromKeychain(keyName: nonExistentKeyName)) { error in
                    if let sshError = error as? SSHManager.SSHError {
                        if case .keychainError = sshError {
                            // Expected
                        } else {
                            XCTFail("Expected keychain error, got \\(sshError)")
                        }
                    } else {
                        XCTFail("Expected SSHError, got \\(error)")
                    }
                }
                
                // Try to retrieve non-existent public key
                XCTAssertThrowsError(try self.sshManager.getPublicKeyFromKeychain(keyName: nonExistentKeyName)) { error in
                    if let sshError = error as? SSHManager.SSHError {
                        if case .keychainError = sshError {
                            // Expected
                        } else {
                            XCTFail("Expected keychain error, got \\(sshError)")
                        }
                    } else {
                        XCTFail("Expected SSHError, got \\(error)")
                    }
                }
                
                expectation.fulfill()
                
            } catch {
                XCTFail("Invalid key retrieval test failed: \\(error.localizedDescription)")
                expectation.fulfill()
            }
        }
        
        wait(for: [expectation], timeout: 10.0)
    }

    func testConnectionStateManagement() {
        let expectation = XCTestExpectation(description: "Connection state management")
        
        DispatchQueue.global().async {
            do {
                // Test initial state
                XCTAssertFalse(self.sshManager.isConnected, "Should start disconnected")
                XCTAssertEqual(self.sshManager.connectionStatus, "Disconnected", "Should show disconnected status")
                
                // Test disconnect when already disconnected (should not crash)
                self.sshManager.disconnect()
                XCTAssertFalse(self.sshManager.isConnected, "Should remain disconnected")
                
                // Test command execution when disconnected
                let commandExpectation = XCTestExpectation(description: "Command execution when disconnected")
                
                self.sshManager.executeCommand("echo test") { result in
                    switch result {
                    case .success:
                        XCTFail("Command should not succeed when disconnected")
                    case .failure(let error):
                        if let sshError = error as? SSHManager.SSHError {
                            XCTAssertEqual(sshError, SSHManager.SSHError.notConnected)
                        } else {
                            XCTFail("Expected SSHError.notConnected, got \\(error)")
                        }
                    }
                    commandExpectation.fulfill()
                }
                
                self.wait(for: [commandExpectation], timeout: 5.0)
                
                expectation.fulfill()
                
            } catch {
                XCTFail("Connection state test failed: \\(error.localizedDescription)")
                expectation.fulfill()
            }
        }
        
        wait(for: [expectation], timeout: 10.0)
    }
}