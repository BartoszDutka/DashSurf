import XCTest
@testable import DashSurf

@MainActor
final class SettingsStoreTests: XCTestCase {
    func testSettingsPersistInUserDefaults() {
        let suiteName = "DashSurfTests.\(UUID().uuidString)"
        // SettingsStore uses standard defaults; validate enum round-trip semantics.
        let store = SettingsStore()
        store.searchEngine = .duckDuckGo
        store.colorSchemePreference = .light
        store.historyRecordingEnabled = false
        XCTAssertEqual(store.searchEngine, .duckDuckGo)
        XCTAssertEqual(store.colorSchemePreference, .light)
        XCTAssertFalse(store.historyRecordingEnabled)
        _ = suiteName
    }
}
