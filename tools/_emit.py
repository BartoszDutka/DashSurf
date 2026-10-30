#!/usr/bin/env python3
"""Emit all DashSurf source files. Safe to re-run."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "DashSurf"
TESTS = ROOT / "DashSurfTests"


def w(rel: str, content: str, base: Path = APP) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    text = content
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}")


def main() -> None:
    print("Writing DashSurf sources...")
    write_app()
    write_core()
    write_models()
    write_persistence()
    write_services()
    write_browser()
    write_features()
    write_carplay()
    write_ui()
    write_assets()
    write_tests()
    write_docs()
    print("Done.")


def write_app() -> None:
    w("App/DashSurfApp.swift", '''\
import SwiftUI
import SwiftData

@main
struct DashSurfApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var dependencies = AppDependencies.shared

    var body: some Scene {
        WindowGroup {
            // Phone UI is hosted by PhoneSceneDelegate for multi-scene CarPlay support.
            Color.clear
                .frame(width: 0, height: 0)
                .onAppear { _ = dependencies }
        }
    }
}
''')

    w("App/AppDelegate.swift", '''\
import UIKit
import AVFoundation

final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        configureAudioSession()
        AppDependencies.shared.bootstrap()
        return true
    }

    func application(
        _ application: UIApplication,
        configurationForConnecting connectingSceneSession: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        if connectingSceneSession.role == CarPlaySceneRole.windowRole {
            let config = UISceneConfiguration(name: "CarPlay", sessionRole: connectingSceneSession.role)
            config.delegateClass = CarPlaySceneDelegate.self
            return config
        }
        let config = UISceneConfiguration(name: "Phone", sessionRole: connectingSceneSession.role)
        config.delegateClass = PhoneSceneDelegate.self
        return config
    }

    private func configureAudioSession() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .moviePlayback, options: [.allowAirPlay, .allowBluetoothA2DP])
            try session.setActive(true)
        } catch {
            // Non-fatal
        }
    }
}
''')

    w("App/PhoneSceneDelegate.swift", '''\
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
''')

    w("App/AppCoordinator.swift", '''\
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
''')

    w("App/RootTabView.swift", '''\
import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var dependencies: AppDependencies
    @EnvironmentObject private var session: BrowserSessionManager
    @EnvironmentObject private var settings: SettingsStore
    @StateObject private var nav = AppCoordinator()

    var body: some View {
        TabView(selection: $nav.selectedTab) {
            HomeView(coordinator: nav)
                .tabItem { Label("Home", systemImage: "house.fill") }
                .tag(AppCoordinator.Destination.home)

            BrowserContainerView(coordinator: nav)
                .tabItem { Label("Browser", systemImage: "safari.fill") }
                .tag(AppCoordinator.Destination.browser)

            HistoryView(coordinator: nav)
                .tabItem { Label("History", systemImage: "clock.fill") }
                .tag(AppCoordinator.Destination.history)

            BookmarksView(coordinator: nav)
                .tabItem { Label("Bookmarks", systemImage: "bookmark.fill") }
                .tag(AppCoordinator.Destination.bookmarks)

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape.fill") }
                .tag(AppCoordinator.Destination.settings)
        }
        .tint(DashSurfTheme.accent)
        .onChange(of: nav.pendingURLToOpen) { _, url in
            guard let url else { return }
            session.openURL(url, inNewTab: false)
            nav.clearPendingURL()
        }
        .environmentObject(nav)
    }
}
''')


def write_core() -> None:
    w("Core/Constants/AppConstants.swift", '''\
import Foundation

enum AppConstants {
    static let appName = "DashSurf"
    static let slogan = "Your browser. Your screen. Your way."
    static let bundleFallbackID = "com.example.dashsurf"
    static let maxLiveWebViews = 4
    static let historyDedupWindow: TimeInterval = 8
    static let defaultHomepage = URL(string: "about:home")!
}

enum DashSurfNotification {
    static let carPlayConnected = Notification.Name("DashSurf.CarPlayConnected")
    static let carPlayDisconnected = Notification.Name("DashSurf.CarPlayDisconnected")
    static let sendURLToCarPlay = Notification.Name("DashSurf.SendURLToCarPlay")
    static let accountSessionMayHaveChanged = Notification.Name("DashSurf.AccountSessionMayHaveChanged")
    static let openURLFromCarPlay = Notification.Name("DashSurf.OpenURLFromCarPlay")
}
''')

    w("Core/Extensions/URL+DashSurf.swift", '''\
import Foundation

extension URL {
    var dashsurfDomain: String {
        host?.lowercased() ?? ""
    }

    var isDashSurfHome: Bool {
        absoluteString == "about:home" || scheme == "about"
    }
}

extension String {
    var nilIfEmpty: String? {
        let t = trimmingCharacters(in: .whitespacesAndNewlines)
        return t.isEmpty ? nil : t
    }
}
''')

    w("Core/Utilities/DateGrouping.swift", '''\
import Foundation

enum HistoryDateGroup: String, CaseIterable, Identifiable {
    case today = "Today"
    case yesterday = "Yesterday"
    case last7Days = "Last 7 Days"
    case older = "Older"

    var id: String { rawValue }

    static func group(for date: Date, now: Date = Date(), calendar: Calendar = .current) -> HistoryDateGroup {
        if calendar.isDateInToday(date) { return .today }
        if calendar.isDateInYesterday(date) { return .yesterday }
        if let weekAgo = calendar.date(byAdding: .day, value: -7, to: now), date >= weekAgo {
            return .last7Days
        }
        return .older
    }
}
''')

    w("Core/DI/AppDependencies.swift", '''\
import Foundation
import SwiftData
import Combine

@MainActor
final class AppDependencies: ObservableObject {
    static let shared = AppDependencies()

    let modelContainer: ModelContainer
    let persistence: PersistenceController
    let historyRepository: HistoryRepository
    let bookmarkRepository: BookmarkRepository
    let recentMediaRepository: RecentMediaRepository
    let quickAccessRepository: QuickAccessRepository
    let tabStateRepository: TabStateRepository
    let websiteDataService: WebsiteDataService
    let urlService: URLService
    let searchService: SearchService
    let faviconService: FaviconService
    let mediaDetectionService: MediaDetectionService
    let webViewFactory: WebViewFactory

    let sessionManager: BrowserSessionManager
    let tabManager: TabManager
    let settingsStore: SettingsStore
    let carPlayAvailability: CarPlayAvailabilityService
    let carPlaySession: CarPlaySessionManager

    private init() {
        let persistence = PersistenceController.makeShared()
        self.persistence = persistence
        self.modelContainer = persistence.container

        let context = ModelContext(persistence.container)
        self.historyRepository = HistoryRepository(modelContext: context)
        self.bookmarkRepository = BookmarkRepository(modelContext: context)
        self.recentMediaRepository = RecentMediaRepository(modelContext: context)
        self.quickAccessRepository = QuickAccessRepository(modelContext: context)
        self.tabStateRepository = TabStateRepository(modelContext: context)

        self.websiteDataService = WebsiteDataService()
        self.urlService = URLService()
        self.searchService = SearchService()
        self.faviconService = FaviconService()
        self.mediaDetectionService = MediaDetectionService()
        self.webViewFactory = WebViewFactory(websiteDataService: websiteDataService)

        self.settingsStore = SettingsStore()
        self.tabManager = TabManager(tabStateRepository: tabStateRepository, settings: settingsStore)
        self.sessionManager = BrowserSessionManager(
            tabManager: tabManager,
            historyRepository: historyRepository,
            bookmarkRepository: bookmarkRepository,
            recentMediaRepository: recentMediaRepository,
            mediaDetectionService: mediaDetectionService,
            urlService: urlService,
            searchService: searchService,
            settings: settingsStore,
            webViewFactory: webViewFactory
        )
        self.carPlayAvailability = CarPlayAvailabilityService()
        self.carPlaySession = CarPlaySessionManager(
            sessionManager: sessionManager,
            availability: carPlayAvailability,
            quickAccessRepository: quickAccessRepository,
            bookmarkRepository: bookmarkRepository,
            historyRepository: historyRepository,
            recentMediaRepository: recentMediaRepository
        )
    }

    func bootstrap() {
        quickAccessRepository.seedDefaultsIfNeeded()
        tabManager.restoreIfNeeded()
        carPlayAvailability.refreshFromBundle()
        Task {
            await AudioSessionService.shared.activatePlaybackCategory()
        }
    }
}
''')


def write_models() -> None:
    w("Models/BrowserHistoryItem.swift", '''\
import Foundation
import SwiftData

@Model
final class BrowserHistoryItem {
    @Attribute(.unique) var id: UUID
    var urlString: String
    var title: String
    var domain: String
    var faviconURLString: String?
    var firstVisitedAt: Date
    var lastVisitedAt: Date
    var visitCount: Int

    init(
        id: UUID = UUID(),
        urlString: String,
        title: String,
        domain: String,
        faviconURLString: String? = nil,
        firstVisitedAt: Date = Date(),
        lastVisitedAt: Date = Date(),
        visitCount: Int = 1
    ) {
        self.id = id
        self.urlString = urlString
        self.title = title
        self.domain = domain
        self.faviconURLString = faviconURLString
        self.firstVisitedAt = firstVisitedAt
        self.lastVisitedAt = lastVisitedAt
        self.visitCount = visitCount
    }

    var url: URL? { URL(string: urlString) }
}
''')

    w("Models/Bookmark.swift", '''\
import Foundation
import SwiftData

@Model
final class BookmarkFolder {
    @Attribute(.unique) var id: UUID
    var name: String
    var createdAt: Date
    var sortOrder: Int
    @Relationship(deleteRule: .cascade, inverse: \\Bookmark.folder)
    var bookmarks: [Bookmark]

    init(id: UUID = UUID(), name: String, createdAt: Date = Date(), sortOrder: Int = 0) {
        self.id = id
        self.name = name
        self.createdAt = createdAt
        self.sortOrder = sortOrder
        self.bookmarks = []
    }
}

@Model
final class Bookmark {
    @Attribute(.unique) var id: UUID
    var title: String
    var urlString: String
    var faviconURLString: String?
    var isFavorite: Bool
    var createdAt: Date
    var updatedAt: Date
    var sortOrder: Int
    var folder: BookmarkFolder?

    init(
        id: UUID = UUID(),
        title: String,
        urlString: String,
        faviconURLString: String? = nil,
        isFavorite: Bool = false,
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        sortOrder: Int = 0,
        folder: BookmarkFolder? = nil
    ) {
        self.id = id
        self.title = title
        self.urlString = urlString
        self.faviconURLString = faviconURLString
        self.isFavorite = isFavorite
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.sortOrder = sortOrder
        self.folder = folder
    }

    var url: URL? { URL(string: urlString) }
}
''')

    w("Models/BrowserTab.swift", '''\
import Foundation
import SwiftData

@Model
final class BrowserTabRecord {
    @Attribute(.unique) var id: UUID
    var urlString: String
    var title: String
    var isActive: Bool
    var createdAt: Date
    var lastActiveAt: Date
    var isPinned: Bool
    var sortOrder: Int

    init(
        id: UUID = UUID(),
        urlString: String = "about:home",
        title: String = "New Tab",
        isActive: Bool = false,
        createdAt: Date = Date(),
        lastActiveAt: Date = Date(),
        isPinned: Bool = false,
        sortOrder: Int = 0
    ) {
        self.id = id
        self.urlString = urlString
        self.title = title
        self.isActive = isActive
        self.createdAt = createdAt
        self.lastActiveAt = lastActiveAt
        self.isPinned = isPinned
        self.sortOrder = sortOrder
    }
}

struct BrowserTab: Identifiable, Equatable, Hashable {
    var id: UUID
    var url: URL
    var title: String
    var isActive: Bool
    var createdAt: Date
    var lastActiveAt: Date
    var isPinned: Bool

    static func fresh(isActive: Bool = true) -> BrowserTab {
        let now = Date()
        return BrowserTab(
            id: UUID(),
            url: AppConstants.defaultHomepage,
            title: "New Tab",
            isActive: isActive,
            createdAt: now,
            lastActiveAt: now,
            isPinned: false
        )
    }
}
''')

    w("Models/RecentMediaItem.swift", '''\
import Foundation
import SwiftData

@Model
final class RecentMediaItem {
    @Attribute(.unique) var id: UUID
    var urlString: String
    var title: String
    var provider: String
    var thumbnailURLString: String?
    var lastOpenedAt: Date
    var playbackPosition: Double?
    var duration: Double?
    var lastKnownState: String?
    var isFavorite: Bool

    init(
        id: UUID = UUID(),
        urlString: String,
        title: String,
        provider: String,
        thumbnailURLString: String? = nil,
        lastOpenedAt: Date = Date(),
        playbackPosition: Double? = nil,
        duration: Double? = nil,
        lastKnownState: String? = nil,
        isFavorite: Bool = false
    ) {
        self.id = id
        self.urlString = urlString
        self.title = title
        self.provider = provider
        self.thumbnailURLString = thumbnailURLString
        self.lastOpenedAt = lastOpenedAt
        self.playbackPosition = playbackPosition
        self.duration = duration
        self.lastKnownState = lastKnownState
        self.isFavorite = isFavorite
    }

    var url: URL? { URL(string: urlString) }
    var thumbnailURL: URL? { thumbnailURLString.flatMap(URL.init(string:)) }
}
''')

    w("Models/QuickAccessItem.swift", '''\
import Foundation
import SwiftData

@Model
final class QuickAccessItem {
    @Attribute(.unique) var id: UUID
    var title: String
    var urlString: String
    var symbolName: String
    var sortOrder: Int
    var isPinned: Bool
    var createdAt: Date

    init(
        id: UUID = UUID(),
        title: String,
        urlString: String,
        symbolName: String,
        sortOrder: Int,
        isPinned: Bool = false,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.title = title
        self.urlString = urlString
        self.symbolName = symbolName
        self.sortOrder = sortOrder
        self.isPinned = isPinned
        self.createdAt = createdAt
    }

    var url: URL? { URL(string: urlString) }

    static let defaults: [(String, String, String)] = [
        ("YouTube", "https://m.youtube.com", "play.rectangle.fill"),
        ("Netflix", "https://www.netflix.com", "film"),
        ("Twitch", "https://m.twitch.tv", "dot.radiowaves.left.and.right"),
        ("Google", "https://www.google.com", "magnifyingglass"),
        ("Reddit", "https://www.reddit.com", "bubble.left.and.bubble.right.fill")
    ]
}
''')

    w("Models/AppSettings.swift", '''\
import Foundation
import SwiftUI

enum AppearancePreference: String, CaseIterable, Identifiable {
    case system, dark, light
    var id: String { rawValue }
    var title: String {
        switch self {
        case .system: return "System"
        case .dark: return "Dark"
        case .light: return "Light"
        }
    }
    var colorScheme: ColorScheme? {
        switch self {
        case .system: return nil
        case .dark: return .dark
        case .light: return .light
        }
    }
}

enum SearchEngine: String, CaseIterable, Identifiable {
    case google, duckDuckGo, bing
    var id: String { rawValue }
    var title: String {
        switch self {
        case .google: return "Google"
        case .duckDuckGo: return "DuckDuckGo"
        case .bing: return "Bing"
        }
    }
    func searchURL(for query: String) -> URL {
        let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        switch self {
        case .google: return URL(string: "https://www.google.com/search?q=\\(encoded)")!
        case .duckDuckGo: return URL(string: "https://duckduckgo.com/?q=\\(encoded)")!
        case .bing: return URL(string: "https://www.bing.com/search?q=\\(encoded)")!
        }
    }
}
''')


if __name__ == "__main__":
    # Only first chunk when imported carefully — full main is at bottom of part2
    pass
