import Foundation
import Combine

/// Shared logical state between iPhone UI and optional CarPlay window.
/// Does not move WKWebView instances across screens.
@MainActor
final class CarPlaySessionManager: ObservableObject {
    @Published var lastURLSentToCar: URL?

    private let sessionManager: BrowserSessionManager
    let availability: CarPlayAvailabilityService
    private let quickAccessRepository: QuickAccessRepository
    private let bookmarkRepository: BookmarkRepository
    private let historyRepository: HistoryRepository
    private let recentMediaRepository: RecentMediaRepository

    init(
        sessionManager: BrowserSessionManager,
        availability: CarPlayAvailabilityService,
        quickAccessRepository: QuickAccessRepository,
        bookmarkRepository: BookmarkRepository,
        historyRepository: HistoryRepository,
        recentMediaRepository: RecentMediaRepository
    ) {
        self.sessionManager = sessionManager
        self.availability = availability
        self.quickAccessRepository = quickAccessRepository
        self.bookmarkRepository = bookmarkRepository
        self.historyRepository = historyRepository
        self.recentMediaRepository = recentMediaRepository
    }

    func sendActivePageToCar() {
        let url = sessionManager.currentURL
        lastURLSentToCar = url
        NotificationCenter.default.post(name: DashSurfNotification.sendURLToCarPlay, object: url)
    }

    func quickAccess() -> [QuickAccessItem] {
        (try? quickAccessRepository.all()) ?? []
    }

    func favoriteBookmarks() -> [Bookmark] {
        (try? bookmarkRepository.favorites()) ?? []
    }

    func recentHistory(limit: Int = 20) -> [BrowserHistoryItem] {
        (try? historyRepository.recent(limit: limit)) ?? []
    }

    func continueWatching(limit: Int = 12) -> [RecentMediaItem] {
        Array(((try? recentMediaRepository.recent(limit: limit)) ?? []).prefix(limit))
    }
}
