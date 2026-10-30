import Foundation
import Combine

@MainActor
final class AppCoordinator: ObservableObject {
    enum Destination: Equatable {
        case home
        case browser
        case history
        case bookmarks
        case settings
    }

    @Published var selectedTab: Destination = .home
    @Published var pendingURLToOpen: URL?

    func openInBrowser(_ url: URL) {
        pendingURLToOpen = url
        selectedTab = .browser
    }

    func clearPendingURL() {
        pendingURLToOpen = nil
    }
}
