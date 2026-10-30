import UIKit
import SwiftUI

final class PhoneSceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }
        let dependencies = AppDependencies.shared
        let root = RootTabView()
            .environmentObject(dependencies)
            .environmentObject(dependencies.sessionManager)
            .environmentObject(dependencies.tabManager)
            .environmentObject(dependencies.settingsStore)
            .environmentObject(dependencies.carPlayAvailability)
            .modelContainer(dependencies.modelContainer)
            .preferredColorScheme(dependencies.settingsStore.colorSchemePreference.colorScheme)

        let controller = UIHostingController(rootView: root)
        let window = UIWindow(windowScene: windowScene)
        window.rootViewController = controller
        window.tintColor = UIColor(DashSurfTheme.accent)
        window.makeKeyAndVisible()
        self.window = window
        dependencies.carPlayAvailability.notePhoneSceneConnected()
    }

    func sceneDidDisconnect(_ scene: UIScene) {
        window = nil
    }
}
