import SwiftUI

/// A SwiftUI calculator view that provides a complete calculator interface
struct CalculatorView: View {
    @StateObject private var viewModel = CalculatorViewModel()
    
    var body: some View {
        VStack(spacing: 12) {
            // Display
            calculatorDisplay
            
            // Button grid
            calculatorButtons
        }
        .padding()
        .background(Color.black)
        .frame(minWidth: 300, minHeight: 400)
    }
    
    /// The calculator display showing current value
    private var calculatorDisplay: some View {
        Text(viewModel.displayValue)
            .font(.system(size: 72, weight: .light))
            .foregroundColor(.white)
            .frame(maxWidth: .infinity, alignment: .trailing)
            .padding(.vertical, 20)
            .padding(.horizontal, 20)
            .lineLimit(1)
            .minimumScaleFactor(0.5)
    }
    
    /// The calculator button grid
    private var calculatorButtons: some View {
        VStack(spacing: 12) {
            ForEach(viewModel.buttonRows, id: \.self) { row in
                HStack(spacing: 12) {
                    ForEach(row, id: \.self) { button in
                        CalculatorButton(
                            title: button.title,
                            color: button.color,
                            action: button.action
                        )
                    }
                }
            }
        }
    }
}

/// A single calculator button
struct CalculatorButton: View {
    let title: String
    let color: Color
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 32, weight: .medium))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .buttonStyle(CalculatorButtonStyle(color: color))
    }
}

/// Custom button style for calculator buttons
struct CalculatorButtonStyle: ButtonStyle {
    let color: Color
    
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .background(color)
            .cornerRadius(40)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.spring(), value: configuration.isPressed)
    }
}

/// ViewModel for calculator logic and state
class CalculatorViewModel: ObservableObject {
    @Published var displayValue: String = "0"
    
    private var currentValue: Double = 0
    private var pendingValue: Double?
    private var pendingOperation: String?
    private var waitingForOperand = false
    
    // Button configuration
    var buttonRows: [[CalculatorButtonConfig]] = []
    
    init() {
        // Initialize button rows
        buttonRows = [
            [
                CalculatorButtonConfig(title: "AC", color: .gray.opacity(0.5), actionType: .clear),
                CalculatorButtonConfig(title: "±", color: .gray.opacity(0.5), actionType: .toggleSign),
                CalculatorButtonConfig(title: "%", color: .gray.opacity(0.5), actionType: .percentage),
                CalculatorButtonConfig(title: "÷", color: .orange, actionType: .operation)
            ],
            [
                CalculatorButtonConfig(title: "7", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: "8", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: "9", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: "×", color: .orange, actionType: .operation)
            ],
            [
                CalculatorButtonConfig(title: "4", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: "5", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: "6", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: "-", color: .orange, actionType: .operation)
            ],
            [
                CalculatorButtonConfig(title: "1", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: "2", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: "3", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: "+", color: .orange, actionType: .operation)
            ],
            [
                CalculatorButtonConfig(title: "0", color: .gray.opacity(0.3), actionType: .digit),
                CalculatorButtonConfig(title: ".", color: .gray.opacity(0.3), actionType: .decimal),
                CalculatorButtonConfig(title: "=", color: .orange, actionType: .equals)
            ]
        ]
        
        // Set up button actions
        for i in 0..<buttonRows.count {
            for j in 0..<buttonRows[i].count {
                var button = buttonRows[i][j]
                button.action = { [weak self] in
                    self?.handleButtonPress(button)
                }
                buttonRows[i][j] = button
            }
        }
    }
    
    private func handleButtonPress(_ button: CalculatorButtonConfig) {
        switch button.actionType {
        case .clear:
            clear()
        case .toggleSign:
            toggleSign()
        case .percentage:
            percentage()
        case .operation:
            setOperation(button.title)
        case .equals:
            performOperation()
        case .digit:
            appendDigit(button.title)
        case .decimal:
            appendDigit(button.title)
        }
    }
    
    // MARK: - Calculator Logic
    
    func clear() {
        currentValue = 0
        pendingValue = nil
        pendingOperation = nil
        waitingForOperand = false
        updateDisplay()
    }
    
    func toggleSign() {
        currentValue = -currentValue
        updateDisplay()
    }
    
    func percentage() {
        currentValue = currentValue / 100
        updateDisplay()
    }
    
    func appendDigit(_ digit: String) {
        if waitingForOperand {
            currentValue = 0
            waitingForOperand = false
        }

        if digit == "." {
            if !displayValue.contains(".") {
                currentValue = Double(displayValue + ".") ?? currentValue
            }
        } else {
            if displayValue == "0" || displayValue == "-0" {
                currentValue = Double(digit) ?? 0
            } else {
                currentValue = Double(displayValue + digit) ?? currentValue
            }
        }
        updateDisplay()
    }
    
    func setOperation(_ operation: String) {
        if waitingForOperand {
            pendingOperation = operation
            return
        }

        if pendingOperation != nil {
            performOperation()
        } else {
            pendingValue = currentValue
        }

        pendingOperation = operation
        waitingForOperand = true
    }
    
    func performOperation() {
        guard let pendingOp = pendingOperation, let pendingVal = pendingValue else { return }

        switch pendingOp {
        case "+":
            currentValue = pendingVal + currentValue
        case "-":
            currentValue = pendingVal - currentValue
        case "×":
            currentValue = pendingVal * currentValue
        case "÷":
            currentValue = pendingVal / currentValue
        default:
            break
        }

        pendingValue = nil
        pendingOperation = nil
        waitingForOperand = true
        updateDisplay()
    }
    
    private func updateDisplay() {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 8
        formatter.numberStyle = .decimal

        let number = NSNumber(value: currentValue)
        let stringValue = formatter.string(from: number) ?? "0"

        // Remove unnecessary decimal places
        if stringValue.hasSuffix(".0") {
            displayValue = String(stringValue.dropLast(2))
        } else {
            displayValue = stringValue
        }
    }
}

/// Button configuration structure
struct CalculatorButtonConfig: Hashable {
    let title: String
    let color: Color
    let actionType: CalculatorButtonActionType
    var action: () -> Void = {}
    
    static func == (lhs: CalculatorButtonConfig, rhs: CalculatorButtonConfig) -> Bool {
        lhs.title == rhs.title && lhs.color == rhs.color && lhs.actionType == rhs.actionType
    }
    
    func hash(into hasher: inout Hasher) {
        hasher.combine(title)
        hasher.combine(color)
        hasher.combine(actionType)
    }
}

/// Button action types
enum CalculatorButtonActionType: Hashable {
    case clear, toggleSign, percentage, operation, equals, digit, decimal
}

// MARK: - Previews

struct CalculatorView_Previews: PreviewProvider {
    static var previews: some View {
        CalculatorView()
            .frame(width: 350, height: 500)
            .previewLayout(.sizeThatFits)
    }
}

struct CalculatorButton_Previews: PreviewProvider {
    static var previews: some View {
        CalculatorButton(title: "5", color: .gray.opacity(0.3), action: {})
            .frame(width: 80, height: 80)
            .previewLayout(.sizeThatFits)
    }
}