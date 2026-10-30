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
