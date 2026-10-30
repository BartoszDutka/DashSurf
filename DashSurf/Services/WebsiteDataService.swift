import Foundation
import WebKit

/// Owns the persistent website data store used by all DashSurf WKWebViews.
final class WebsiteDataService {
    /// Critical: use the default persistent store so cookies / localStorage survive relaunches.
    let dataStore: WKWebsiteDataStore = .default()

    func makeConfiguration(desktopMode: Bool) -> WKWebViewConfiguration {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = dataStore
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        config.allowsPictureInPictureMediaPlayback = true
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        config.defaultWebpagePreferences.preferredContentMode = desktopMode ? .desktop : .mobile

        let preferences = WKPreferences()
        preferences.javaScriptCanOpenWindowsAutomatically = true
        config.preferences = preferences

        return config
    }

    func clearAllWebsiteData() async {
        let types = WKWebsiteDataStore.allWebsiteDataTypes()
        let records = await dataStore.dataRecords(ofTypes: types)
        await dataStore.removeData(ofTypes: types, for: records)
    }

    func clearData(forDomain domain: String) async {
        let types = WKWebsiteDataStore.allWebsiteDataTypes()
        let records = await dataStore.dataRecords(ofTypes: types)
        let matched = records.filter {
            $0.displayName.lowercased().contains(domain.lowercased())
        }
        await dataStore.removeData(ofTypes: types, for: matched)
    }
}
