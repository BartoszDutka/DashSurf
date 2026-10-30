import UIKit

/// Hosts an optional car UIWindowScene when Apple has granted CarPlay entitlements.
/// Inspired by the MIT-licensed Cafari Lite scene pattern; DashSurf UI and data layer are original.
final class CarPlaySceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: windowScene)
        let controller = CarPlayBrowserViewController(
            sessionManager: AppDependencies.shared.sessionManager,
            carPlaySession: AppDependencies.shared.carPlaySession
        )
        window.rootViewController = controller
        window.makeKeyAndVisible()
        self.window = window
        Task { @MainActor in
            CarPlayCoordinator.shared.attach(window: window, controller: controller)
        }
    }

    func sceneDidDisconnect(_ scene: UIScene) {
        window = nil
        Task { @MainActor in
            CarPlayCoordinator.shared.detach()
        }
    }
}
