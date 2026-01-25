import XCTest
@testable import CalculatorApp

class CalculatorBrainTests: XCTestCase {

    var calculatorViewModel: CalculatorViewModel.TestableCalculatorViewModel!

    override func setUp() {
        super.setUp()
        calculatorViewModel = CalculatorViewModel.TestableCalculatorViewModel()
    }

    override func tearDown() {
        calculatorViewModel = nil
        super.tearDown()
    }

    func testInitialState() {
        XCTAssertEqual(calculatorViewModel.displayValue, "0")
    }

    func testClear() {
        calculatorViewModel.testAppendDigit("5")
        calculatorViewModel.testClear()
        XCTAssertEqual(calculatorViewModel.displayValue, "0")
    }

    func testToggleSign() {
        calculatorViewModel.testAppendDigit("5")
        calculatorViewModel.testToggleSign()
        XCTAssertEqual(calculatorViewModel.displayValue, "-5")
        
        calculatorViewModel.testToggleSign()
        XCTAssertEqual(calculatorViewModel.displayValue, "5")
    }

    func testPercentage() {
        calculatorViewModel.testAppendDigit("5")
        calculatorViewModel.testAppendDigit("0")
        calculatorViewModel.testPercentage()
        XCTAssertEqual(calculatorViewModel.displayValue, "0.5")
    }

    func testBasicAddition() {
        calculatorViewModel.testAppendDigit("5")
        calculatorViewModel.testSetOperation("+")
        calculatorViewModel.testAppendDigit("3")
        calculatorViewModel.testPerformOperation()
        XCTAssertEqual(calculatorViewModel.displayValue, "8")
    }

    func testBasicSubtraction() {
        calculatorViewModel.testAppendDigit("1")
        calculatorViewModel.testAppendDigit("0")
        calculatorViewModel.testSetOperation("-")
        calculatorViewModel.testAppendDigit("3")
        calculatorViewModel.testPerformOperation()
        XCTAssertEqual(calculatorViewModel.displayValue, "7")
    }

    func testBasicMultiplication() {
        calculatorViewModel.testAppendDigit("4")
        calculatorViewModel.testSetOperation("×")
        calculatorViewModel.testAppendDigit("3")
        calculatorViewModel.testPerformOperation()
        XCTAssertEqual(calculatorViewModel.displayValue, "12")
    }

    func testBasicDivision() {
        calculatorViewModel.testAppendDigit("1")
        calculatorViewModel.testAppendDigit("2")
        calculatorViewModel.testSetOperation("÷")
        calculatorViewModel.testAppendDigit("3")
        calculatorViewModel.testPerformOperation()
        XCTAssertEqual(calculatorViewModel.displayValue, "4")
    }

    func testDecimalInput() {
        calculatorViewModel.testAppendDigit("1")
        calculatorViewModel.testAppendDigit(".")
        calculatorViewModel.testAppendDigit("5")
        XCTAssertEqual(calculatorViewModel.displayValue, "1.5")
    }

    func testChainedOperations() {
        calculatorViewModel.testAppendDigit("5")
        calculatorViewModel.testSetOperation("+")
        calculatorViewModel.testAppendDigit("3")
        calculatorViewModel.testPerformOperation()
        calculatorViewModel.testSetOperation("×")
        calculatorViewModel.testAppendDigit("2")
        calculatorViewModel.testPerformOperation()
        XCTAssertEqual(calculatorViewModel.displayValue, "16")
    }

    func testDisplayFormatting() {
        // Test that .0 is removed for integers
        calculatorViewModel.testAppendDigit("5")
        calculatorViewModel.testAppendDigit(".")
        calculatorViewModel.testAppendDigit("0")
        XCTAssertEqual(calculatorViewModel.displayValue, "5")
        
        // Test decimal places are preserved when needed
        calculatorViewModel.testClear()
        calculatorViewModel.testAppendDigit("1")
        calculatorViewModel.testAppendDigit(".")
        calculatorViewModel.testAppendDigit("2")
        calculatorViewModel.testAppendDigit("5")
        XCTAssertEqual(calculatorViewModel.displayValue, "1.25")
    }
}