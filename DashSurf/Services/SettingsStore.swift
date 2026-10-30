import Foundation
import Combine
import SwiftUI

@MainActor
final class SettingsStore: ObservableObject {
    private enum Keys {
        static let appearance = "settings.appearance"
        static let searchEngine = "settings.searchEngine"
        static let homepage = "settings.homepage"
        static let restoreTabs = "settings.restoreTabs"
        static let desktopMode = "settings.desktopMode"
        static let historyEnabled = "settings.historyEnabled"
    }

    @Published var colorSchemePreference: AppearancePreference {
        didSet { UserDefaults.standard.set(colorSchemePreference.rawValue, forKey: Keys.appearance) }
    }
    @Published var searchEngine: SearchEngine {
        didSet { UserDefaults.standard.set(searchEngine.rawValue, forKey: Keys.searchEngine) }
    }
    @Published var homepageURLString: String {
        didSet { UserDefaults.standard.set(homepageURLString, forKey: Keys.homepage) }
    }
    @Published var restoreTabsOnLaunch: Bool {
        didSet { UserDefaults.standard.set(restoreTabsOnLaunch, forKey: Keys.restoreTabs) }
    }
    @Published var desktopModeDefault: Bool {
        didSet { UserDefaults.standard.set(desktopModeDefault, forKey: Keys.desktopMode) }
    }
    @Published var historyRecordingEnabled: Bool {
        didSet { UserDefaults.standard.set(historyRecordingEnabled, forKey: Keys.historyEnabled) }
    }

    init() {
        let defaults = UserDefaults.standard
        colorSchemePreference = AppearancePreference(rawValue: defaults.string(forKey: Keys.appearance) ?? "") ?? .dark
        searchEngine = SearchEngine(rawValue: defaults.string(forKey: Keys.searchEngine) ?? "") ?? .google
        homepageURLString = defaults.string(forKey: Keys.homepage) ?? "about:home"
        restoreTabsOnLaunch = defaults.object(forKey: Keys.restoreTabs) as? Bool ?? true
        desktopModeDefault = defaults.bool(forKey: Keys.desktopMode)
        if defaults.object(forKey: Keys.historyEnabled) == nil {
            historyRecordingEnabled = true
        } else {
            historyRecordingEnabled = defaults.bool(forKey: Keys.historyEnabled)
        }
    }
}
