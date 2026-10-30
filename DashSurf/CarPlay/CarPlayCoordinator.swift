import UIKit

@MainActor
final class CarPlayCoordinator {
    static let shared = CarPlayCoordinator()

    private(set) weak var carWindow: UIWindow?
    private(set) weak var browserController: CarPlayBrowserViewController?

    func attach(window: UIWindow, controller: CarPlayBrowserViewController) {
        carWindow = window
        browserController = controller
        AppDependencies.shared.carPlayAvailability.noteCarSceneConnected()
        CarMotionGate.shared.start()
    }

    func detach() {
        carWindow = nil
        browserController = nil
        AppDependencies.shared.carPlayAvailability.noteCarSceneDisconnected()
        CarMotionGate.shared.stop()
    }

    func loadURL(_ url: URL) {
        browserController?.load(url: url)
    }
}
