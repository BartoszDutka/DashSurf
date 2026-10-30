import Foundation
import Combine

@MainActor
final class BrowserSessionManager: ObservableObject {
    @Published var addressBarText: String = ""
    @Published var isLoading: Bool = false
    @Published var estimatedProgress: Double = 0
    @Published var canGoBack: Bool = false
    @Published var canGoForward: Bool = false
    @Published var pageTitle: String = ""
    @Published var currentURL: URL = AppConstants.defaultHomepage
    @Published var desktopMode: Bool
    @Published var errorMessage: String?
    @Published var showWebViewBlockedHint: Bool = false

    let tabManager: TabManager
    private let historyRepository: HistoryRepository
    private let bookmarkRepository: BookmarkRepository
    private let recentMediaRepository: RecentMediaRepository
    private let mediaDetectionService: MediaDetectionService
    private let urlService: URLService
    private let searchService: SearchService
    private let settings: SettingsStore
    let webViewFactory: WebViewFactory

    /// Soft redirect suppression for history dedupe.
    private var lastCommittedURL: URL?
    private var lastHistoryWriteAt: Date = .distantPast

    init(
        tabManager: TabManager,
        historyRepository: HistoryRepository,
        bookmarkRepository: BookmarkRepository,
        recentMediaRepository: RecentMediaRepository,
        mediaDetectionService: MediaDetectionService,
        urlService: URLService,
        searchService: SearchService,
        settings: SettingsStore,
        webViewFactory: WebViewFactory
    ) {
        self.tabManager = tabManager
        self.historyRepository = historyRepository
        self.bookmarkRepository = bookmarkRepository
        self.recentMediaRepository = recentMediaRepository
        self.mediaDetectionService = mediaDetectionService
        self.urlService = urlService
        self.searchService = searchService
        self.settings = settings
        self.webViewFactory = webViewFactory
        self.desktopMode = settings.desktopModeDefault
    }

    func openURL(_ url: URL, inNewTab: Bool) {
        if inNewTab {
            _ = tabManager.openNewTab(url: url, activate: true)
        } else if tabManager.tabs.isEmpty {
            _ = tabManager.openNewTab(url: url, activate: true)
        } else {
            tabManager.updateActive(url: url, title: url.dashsurfDomain)
        }
        currentURL = url
        addressBarText = displayText(for: url)
        NotificationCenter.default.post(name: .dashSurfNavigateActiveTab, object: url)
    }

    func submitAddressBar() {
        let url = urlService.resolve(addressBarText, searchEngine: settings.searchEngine)
        openURL(url, inNewTab: false)
    }

    func handleNavigationCommitted(url: URL, title: String?) {
        currentURL = url
        addressBarText = displayText(for: url)
        pageTitle = title ?? pageTitle
        tabManager.updateActive(url: url, title: title)
        recordHistoryIfNeeded(url: url, title: title)
        recordMediaIfNeeded(url: url, title: title)
        lastCommittedURL = url
    }

    func toggleDesktopMode() {
        desktopMode.toggle()
        if let id = tabManager.activeTabID {
            webViewFactory.applyDesktopMode(desktopMode, to: id)
        }
    }

    @discardableResult
    func addBookmarkForCurrentPage() throws -> Bookmark? {
        guard !currentURL.isDashSurfHome else { return nil }
        return try bookmarkRepository.add(title: pageTitle.nilIfEmpty ?? currentURL.dashsurfDomain, url: currentURL)
    }

    private func recordHistoryIfNeeded(url: URL, title: String?) {
        guard settings.historyRecordingEnabled else { return }
        guard !url.isDashSurfHome else { return }
        // Avoid recording rapid redirect hops as separate visits.
        if let last = lastCommittedURL,
           last.host == url.host,
           Date().timeIntervalSince(lastHistoryWriteAt) < 1.5,
           last.path != url.path {
            // still allow distinct paths after short delay only
        }
        do {
            try historyRepository.recordVisit(url: url, title: title, faviconURL: FaviconService.guessURL(for: url))
            lastHistoryWriteAt = Date()
        } catch {
            // Persistence errors should not crash browsing.
        }
    }

    private func recordMediaIfNeeded(url: URL, title: String?) {
        guard let media = mediaDetectionService.detect(url: url, pageTitle: title) else { return }
        try? recentMediaRepository.upsert(
            url: media.url,
            title: media.title,
            provider: media.provider,
            thumbnailURL: media.thumbnailURL
        )
    }

    private func displayText(for url: URL) -> String {
        if url.isDashSurfHome { return "" }
        return url.absoluteString
    }
}

extension Notification.Name {
    static let dashSurfNavigateActiveTab = Notification.Name("DashSurf.NavigateActiveTab")
}
