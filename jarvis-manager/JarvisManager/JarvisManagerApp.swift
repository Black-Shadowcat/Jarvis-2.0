import SwiftUI

@main
struct JarvisManagerApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowStyle(.hiddenTitleBar)
        .windowResizability(.contentSize)
        .commands {
            // Standard-Menueeintraege entfernen die nicht benoetigt werden
            CommandGroup(replacing: .newItem) {}
        }
    }
}
