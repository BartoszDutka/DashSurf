import SwiftUI
import SwiftData

@main
struct DashSurfApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var dependencies = AppDependencies.shared

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(dependencies)
                .environmentObject(dependencies.sessionManager)
                .environmentObject(dependencies.tabManager)
                .environmentObject(dependencies.settingsStore)
                .environmentObject(dependencies.carPlayAvailability)
                .modelContainer(dependencies.modelContainer)
                .preferredColorScheme(dependencies.settingsStore.colorSchemePreference.colorScheme)
        }
        .modelContainer(dependencies.modelContainer)
    }
}
