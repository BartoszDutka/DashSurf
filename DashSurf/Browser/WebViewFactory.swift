import WebKit

@MainActor
final class WebViewFactory {
    private let websiteDataService: WebsiteDataService
    private var pool: [UUID: WKWebView] = [:]

    init(websiteDataService: WebsiteDataService) {
        self.websiteDataService = websiteDataService
    }

    func webView(for tabID: UUID, desktopMode: Bool) -> WKWebView {
        if let existing = pool[tabID] {
            return existing
        }
        evictIfNeeded()
        let config = websiteDataService.makeConfiguration(desktopMode: desktopMode)
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.contentInsetAdjustmentBehavior = .automatic
        webView.isOpaque = false
        webView.backgroundColor = .clear
        #if DEBUG
        if #available(iOS 16.4, *) {
            webView.isInspectable = true
        }
        #endif
        pool[tabID] = webView
        return webView
    }

    func recycle(tabID: UUID) {
        pool[tabID]?.stopLoading()
        pool[tabID]?.navigationDelegate = nil
        pool[tabID]?.uiDelegate = nil
        pool.removeValue(forKey: tabID)
    }

    func applyDesktopMode(_ enabled: Bool, to tabID: UUID) {
        guard let webView = pool[tabID] else { return }
        webView.configuration.defaultWebpagePreferences.preferredContentMode = enabled ? .desktop : .mobile
        webView.reload()
    }

    private func evictIfNeeded() {
        guard pool.count >= AppConstants.maxLiveWebViews else { return }
        // Evict least-recently-created entry that is not the newest.
        if let victim = pool.keys.first {
            recycle(tabID: victim)
        }
    }
}
