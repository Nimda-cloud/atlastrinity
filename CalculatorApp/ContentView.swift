import SwiftUI

struct ContentView: View {
    var body: some View {
        CalculatorView()
            .frame(minWidth: 350, minHeight: 500)
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
            .frame(width: 350, height: 500)
    }
}