import XCTest
import SwiftData
@testable import DashSurf

@MainActor
final class TabManagerTests: XCTestCase {
    func testOpenCloseAndRestoreTabs() throws {
        let persistence = PersistenceController(inMemory: true)
        let settings = SettingsStore()
        settings.restoreTabsOnLaunch = true
        let tabsRepo = TabStateRepository(modelContext: ModelContext(persistence.container))
        let manager = TabManager(tabStateRepository: tabsRepo, settings: settings)
        manager.restoreIfNeeded()
        XCTAssertEqual(manager.tabs.count, 1)
        let second = manager.openNewTab(url: URL(string: "https://example.com")!, activate: true)
        XCTAssertEqual(manager.tabs.count, 2)
        manager.closeTab(id: second.id)
        XCTAssertEqual(manager.tabs.count, 1)

        let restored = TabManager(tabStateRepository: tabsRepo, settings: settings)
        restored.restoreIfNeeded()
        XCTAssertFalse(restored.tabs.isEmpty)
    }
}
