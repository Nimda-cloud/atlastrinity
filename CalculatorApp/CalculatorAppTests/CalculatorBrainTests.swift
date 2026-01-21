import XCTest
@testable import CalculatorApp

class CalculatorBrainTests: XCTestCase {

    var calculatorBrain: CalculatorBrain!

    override func setUp() {
        super.setUp()
        calculatorBrain = CalculatorBrain()
    }

    override func tearDown() {
        calculatorBrain = nil
        super.tearDown()
    }

    func testInitialState() {
        XCTAssertEqual(calculatorBrain.displayValue, "0")
    }

    func testClear() {
        calculatorBrain.appendDigit("5")
        calculatorBrain.clear()
        XCTAssertEqual(calculatorBrain.displayValue, "0")
    }

    func testToggleSign() {
        calculatorBrain.appendDigit("5")
        calculatorBrain.toggleSign()
        XCTAssertEqual(calculatorBrain.displayValue, "-5")
        
        calculatorBrain.toggleSign()
        XCTAssertEqual(calculatorBrain.displayValue, "5")
    }

    func testPercentage() {
        calculatorBrain.appendDigit("5")
        calculatorBrain.appendDigit("0")
        calculatorBrain.percentage()
        XCTAssertEqual(calculatorBrain.displayValue, "0.5")
    }

    func testBasicAddition() {
        calculatorBrain.appendDigit("5")
        calculatorBrain.setOperation("+")
        calculatorBrain.appendDigit("3")
        calculatorBrain.performOperation()
        XCTAssertEqual(calculatorBrain.displayValue, "8")
    }

    func testBasicSubtraction() {
        calculatorBrain.appendDigit("1")
        calculatorBrain.appendDigit("0")
        calculatorBrain.setOperation("-")
        calculatorBrain.appendDigit("3")
        calculatorBrain.performOperation()
        XCTAssertEqual(calculatorBrain.displayValue, "7")
    }

    func testBasicMultiplication() {
        calculatorBrain.appendDigit("4")
        calculatorBrain.setOperation("×")
        calculatorBrain.appendDigit("3")
        calculatorBrain.performOperation()
        XCTAssertEqual(calculatorBrain.displayValue, "12")
    }

    func testBasicDivision() {
        calculatorBrain.appendDigit("1")
        calculatorBrain.appendDigit("2")
        calculatorBrain.setOperation("÷")
        calculatorBrain.appendDigit("3")
        calculatorBrain.performOperation()
        XCTAssertEqual(calculatorBrain.displayValue, "4")
    }

    func testDecimalInput() {
        calculatorBrain.appendDigit("1")
        calculatorBrain.appendDigit(".")
        calculatorBrain.appendDigit("5")
        XCTAssertEqual(calculatorBrain.displayValue, "1.5")
    }

    func testChainedOperations() {
        calculatorBrain.appendDigit("5")
        calculatorBrain.setOperation("+")
        calculatorBrain.appendDigit("3")
        calculatorBrain.performOperation()
        calculatorBrain.setOperation("×")
        calculatorBrain.appendDigit("2")
        calculatorBrain.performOperation()
        XCTAssertEqual(calculatorBrain.displayValue, "16")
    }

    func testDisplayFormatting() {
        // Test that .0 is removed for integers
        calculatorBrain.appendDigit("5")
        calculatorBrain.appendDigit(".")
        calculatorBrain.appendDigit("0")
        XCTAssertEqual(calculatorBrain.displayValue, "5")
        
        // Test decimal places are preserved when needed
        calculatorBrain.clear()
        calculatorBrain.appendDigit("1")
        calculatorBrain.appendDigit(".")
        calculatorBrain.appendDigit("2")
        calculatorBrain.appendDigit("5")
        XCTAssertEqual(calculatorBrain.displayValue, "1.25")
    }
}