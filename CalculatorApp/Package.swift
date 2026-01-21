// swift-tools-version:5.5
import PackageDescription

let package = Package(
    name: "CalculatorApp",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v15)
    ],
    products: [
        .library(
            name: "CalculatorApp",
            targets: ["CalculatorApp"]),
    ],
    targets: [
        .target(
            name: "CalculatorApp",
            dependencies: [],
            path: ".",
            exclude: [
                "Package.swift",
                "CalculatorAppTests",
                "CalculatorAppUITests"
            ],
            resources: [
                .process("CalculatorApp/Assets.xcassets"),
                .process("CalculatorApp/Base.lproj")
            ],
            swiftSettings: [
                .define("DEBUG", .when(configuration: .debug))
            ]
        ),
        .testTarget(
            name: "CalculatorAppTests",
            dependencies: ["CalculatorApp"],
            path: "CalculatorAppTests",
            exclude: [
                "Info.plist"
            ]
        ),
    ]
)