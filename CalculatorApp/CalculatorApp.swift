import SwiftUI

@main
struct CalculatorApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 350, minHeight: 500)
        }
        #if os(macOS)
        .windowStyle(.hiddenTitleBar)
        #endif
    }
}