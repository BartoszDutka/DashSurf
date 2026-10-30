import Foundation
import Combine

@MainActor
final class BrowserViewModel: ObservableObject {
    let session: BrowserSessionManager
    let tabManager: TabManager

    @Published var showTabsSheet = false
    @Published var showMenu = false

    init(session: BrowserSessionManager, tabManager: TabManager) {
        self.session = session
        self.tabManager = tabManager
    }

    func goBack() {
        NotificationCenter.default.post(name: .dashSurfBrowserCommand, object: BrowserCommand.goBack)
    }

    func goForward() {
        NotificationCenter.default.post(name: .dashSurfBrowserCommand, object: BrowserCommand.goForward)
    }

    func reloadOrStop() {
        if session.isLoading {
            NotificationCenter.default.post(name: .dashSurfBrowserCommand, object: BrowserCommand.stop)
        } else {
            NotificationCenter.default.post(name: .dashSurfBrowserCommand, object: BrowserCommand.reload)
        }
    }

    func shareCurrent() -> URL? {
        session.currentURL.isDashSurfHome ? nil : session.currentURL
    }
}

enum BrowserCommand {
    case goBack, goForward, reload, stop
}

extension Notification.Name {
    static let dashSurfBrowserCommand = Notification.Name("DashSurf.BrowserCommand")
}
