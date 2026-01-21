import UIKit

class ViewController: UIViewController {

    // MARK: - Properties
    private var displayLabel: UILabel!
    private var calculatorBrain: CalculatorBrain!

    // MARK: - View Lifecycle
    override func viewDidLoad() {
        super.viewDidLoad()
        setupCalculator()
    }

    // MARK: - Setup
    private func setupCalculator() {
        view.backgroundColor = .black
        calculatorBrain = CalculatorBrain()

        setupDisplay()
        setupButtons()
    }

    private func setupDisplay() {
        displayLabel = UILabel()
        displayLabel.translatesAutoresizingMaskIntoConstraints = false
        displayLabel.text = "0"
        displayLabel.textColor = .white
        displayLabel.textAlignment = .right
        displayLabel.font = UIFont.systemFont(ofSize: 72, weight: .light)
        displayLabel.adjustsFontSizeToFitWidth = true
        displayLabel.minimumScaleFactor = 0.5

        view.addSubview(displayLabel)

        NSLayoutConstraint.activate([
            displayLabel.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 20),
            displayLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            displayLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            displayLabel.heightAnchor.constraint(equalToConstant: 100)
        ])
    }

    private func setupButtons() {
        let buttonTitles = [
            ["AC", "±", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "-"],
            ["1", "2", "3", "+"],
            ["0", ".", "="]
        ]

        let buttonColors: [String: UIColor] = [
            "AC": .lightGray,
            "±": .lightGray,
            "%": .lightGray,
            "÷": .orange,
            "×": .orange,
            "-": .orange,
            "+": .orange,
            "=": .orange,
            "0": .darkGray,
            "1": .darkGray,
            "2": .darkGray,
            "3": .darkGray,
            "4": .darkGray,
            "5": .darkGray,
            "6": .darkGray,
            "7": .darkGray,
            "8": .darkGray,
            "9": .darkGray,
            ".": .darkGray
        ]

        let stackView = UIStackView()
        stackView.translatesAutoresizingMaskIntoConstraints = false
        stackView.axis = .vertical
        stackView.distribution = .fillEqually
        stackView.spacing = 12

        view.addSubview(stackView)

        NSLayoutConstraint.activate([
            stackView.topAnchor.constraint(equalTo: displayLabel.bottomAnchor, constant: 20),
            stackView.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            stackView.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            stackView.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -20)
        ])

        for rowTitles in buttonTitles {
            let rowStackView = UIStackView()
            rowStackView.axis = .horizontal
            rowStackView.distribution = .fillEqually
            rowStackView.spacing = 12

            for title in rowTitles {
                let button = createButton(title: title, color: buttonColors[title] ?? .darkGray)
                rowStackView.addArrangedSubview(button)
            }

            stackView.addArrangedSubview(rowStackView)
        }
    }

    private func createButton(title: String, color: UIColor) -> UIButton {
        let button = UIButton(type: .system)
        button.setTitle(title, for: .normal)
        button.titleLabel?.font = UIFont.systemFont(ofSize: 32, weight: .medium)
        button.setTitleColor(.white, for: .normal)
        button.backgroundColor = color
        button.layer.cornerRadius = 40
        button.addTarget(self, action: #selector(buttonTapped(_:)), for: .touchUpInside)

        // Special styling for zero button
        if title == "0" {
            button.contentHorizontalAlignment = .leading
            button.contentEdgeInsets = UIEdgeInsets(top: 0, left: 32, bottom: 0, right: 0)
        }

        return button
    }

    // MARK: - Button Actions
    @objc private func buttonTapped(_ sender: UIButton) {
        guard let title = sender.titleLabel?.text else { return }

        switch title {
        case "AC":
            calculatorBrain.clear()
            updateDisplay()
        case "±":
            calculatorBrain.toggleSign()
            updateDisplay()
        case "%":
            calculatorBrain.percentage()
            updateDisplay()
        case "=":
            calculatorBrain.performOperation()
            updateDisplay()
        case "+", "-", "×", "÷":
            calculatorBrain.setOperation(title)
        default:
            calculatorBrain.appendDigit(title)
            updateDisplay()
        }
    }

    private func updateDisplay() {
        displayLabel.text = calculatorBrain.displayValue
    }
}

// MARK: - Calculator Brain
class CalculatorBrain {

    private var currentValue: Double = 0
    private var pendingValue: Double?
    private var pendingOperation: String?
    private var waitingForOperand = false

    var displayValue: String {
        let formatter = NumberFormatter()
        formatter.minimumFractionDigits = 0
        formatter.maximumFractionDigits = 8
        formatter.numberStyle = .decimal

        let number = NSNumber(value: currentValue)

        // Remove unnecessary decimal places
        let stringValue = formatter.string(from: number) ?? "0"

        // Remove .0 if it's an integer
        if stringValue.hasSuffix(".0") {
            return String(stringValue.dropLast(2))
        }

        return stringValue
    }

    func clear() {
        currentValue = 0
        pendingValue = nil
        pendingOperation = nil
        waitingForOperand = false
    }

    func toggleSign() {
        currentValue = -currentValue
    }

    func percentage() {
        currentValue = currentValue / 100
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
    }

    func setOperation(_ operation: String) {
        if waitingForOperand {
            pendingOperation = operation
            return
        }

        if let pendingOp = pendingOperation {
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
    }
}

// MARK: - SwiftUI Preview
struct ViewController_Previews: PreviewProvider {
    static var previews: some View {
        ViewControllerRepresentable()
            .edgesIgnoringSafeArea(.all)
    }
}

struct ViewControllerRepresentable: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> ViewController {
        return ViewController()
    }

    func updateUIViewController(_ uiViewController: ViewController, context: Context) {
        // Update the view controller if needed
    }
}