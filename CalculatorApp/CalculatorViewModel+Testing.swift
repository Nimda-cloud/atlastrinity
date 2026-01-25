//  CalculatorViewModel+Testing.swift
//  CalculatorApp
//
//  Created for testing purposes

import Foundation

// MARK: - Testing Extension

extension CalculatorViewModel {
    /// Testable version of CalculatorViewModel that exposes private methods for testing
    class TestableCalculatorViewModel: CalculatorViewModel {
        
        // Override private methods to make them accessible for testing
        override func appendDigit(_ digit: String) {
            super.appendDigit(digit)
        }
        
        override func clear() {
            super.clear()
        }
        
        override func toggleSign() {
            super.toggleSign()
        }
        
        override func percentage() {
            super.percentage()
        }
        
        override func setOperation(_ operation: String) {
            super.setOperation(operation)
        }
        
        override func performOperation() {
            super.performOperation()
        }
        
        // Convenience methods for testing
        func testAppendDigit(_ digit: String) {
            appendDigit(digit)
        }
        
        func testClear() {
            clear()
        }
        
        func testToggleSign() {
            toggleSign()
        }
        
        func testPercentage() {
            percentage()
        }
        
        func testSetOperation(_ operation: String) {
            setOperation(operation)
        }
        
        func testPerformOperation() {
            performOperation()
        }
    }
}