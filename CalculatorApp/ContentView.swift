import SwiftUI

struct ContentView: View {
    var body: some View {
        ViewControllerRepresentable()
            .edgesIgnoringSafeArea(.all)
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}