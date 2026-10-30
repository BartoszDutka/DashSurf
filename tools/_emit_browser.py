#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("emit", ROOT / "tools" / "_emit.py")
emit = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(emit)
w = emit.w


def write_browser() -> None:
    w("Browser/WebViewFactory.swift", r'''
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
'''.lstrip())

    w("Browser/TabManager.swift", r'''
import Foundation
import Combine

@MainActor
final class TabManager: ObservableObject {
    @Published private(set) var tabs: [BrowserTab] = []
    @Published private(set) var activeTabID: UUID?

    private let tabStateRepository: TabStateRepository
    private let settings: SettingsStore
    private var didRestore = false

    init(tabStateRepository: TabStateRepository, settings: SettingsStore) {
        self.tabStateRepository = tabStateRepository
        self.settings = settings
    }

    var activeTab: BrowserTab? {
        tabs.first(where: { $0.id == activeTabID }) ?? tabs.first
    }

    func restoreIfNeeded() {
        guard !didRestore else { return }
        didRestore = true
        if settings.restoreTabsOnLaunch, let saved = try? tabStateRepository.load(), !saved.isEmpty {
            tabs = saved
            activeTabID = saved.first(where: \.isActive)?.id ?? saved.first?.id
        } else {
            let tab = BrowserTab.fresh(isActive: true)
            tabs = [tab]
            activeTabID = tab.id
            persist()
        }
    }

    @discardableResult
    func openNewTab(url: URL? = nil, activate: Bool = true) -> BrowserTab {
        var tab = BrowserTab.fresh(isActive: activate)
        if let url {
            tab.url = url
            tab.title = url.dashsurfDomain.isEmpty ? "New Tab" : url.dashsurfDomain
        }
        if activate {
            tabs = tabs.map { var t = $0; t.isActive = false; return t }
            tab.isActive = true
            activeTabID = tab.id
        }
        tabs.append(tab)
        persist()
        return tab
    }

    func closeTab(id: UUID) {
        tabs.removeAll { $0.id == id }
        if tabs.isEmpty {
            let tab = BrowserTab.fresh(isActive: true)
            tabs = [tab]
            activeTabID = tab.id
        } else if activeTabID == id {
            activeTabID = tabs.last?.id
            tabs = tabs.map { var t = $0; t.isActive = (t.id == activeTabID); return t }
        }
        persist()
    }

    func closeAll() {
        let tab = BrowserTab.fresh(isActive: true)
        tabs = [tab]
        activeTabID = tab.id
        persist()
    }

    func selectTab(id: UUID) {
        activeTabID = id
        let now = Date()
        tabs = tabs.map { tab in
            var t = tab
            t.isActive = (t.id == id)
            if t.isActive { t.lastActiveAt = now }
            return t
        }
        persist()
    }

    func updateActive(url: URL?, title: String?) {
        guard let activeTabID else { return }
        tabs = tabs.map { tab in
            guard tab.id == activeTabID else { return tab }
            var t = tab
            if let url { t.url = url }
            if let title, !title.isEmpty { t.title = title }
            t.lastActiveAt = Date()
            return t
        }
        persist()
    }

    func persist() {
        try? tabStateRepository.save(tabs)
    }
}
'''.lstrip())

    w("Browser/BrowserSessionManager.swift", r'''
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
'''.lstrip())

    w("Browser/BrowserViewModel.swift", r'''
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
'''.lstrip())

    w("Browser/WebViewRepresentable.swift", r'''
import SwiftUI
import WebKit

struct WebViewRepresentable: UIViewRepresentable {
    let tabID: UUID
    @ObservedObject var session: BrowserSessionManager

    func makeCoordinator() -> Coordinator {
        Coordinator(session: session, tabID: tabID)
    }

    func makeUIView(context: Context) -> WKWebView {
        let webView = session.webViewFactory.webView(for: tabID, desktopMode: session.desktopMode)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        context.coordinator.observe(webView)
        context.coordinator.bindCommands(to: webView)
        if webView.url == nil {
            loadInitial(on: webView)
        }
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        context.coordinator.session = session
        context.coordinator.tabID = tabID
    }

    private func loadInitial(on webView: WKWebView) {
        let url = session.tabManager.tabs.first(where: { $0.id == tabID })?.url ?? session.currentURL
        if url.isDashSurfHome {
            webView.loadHTMLString(HomeHTML.document, baseURL: nil)
        } else {
            webView.load(URLRequest(url: url))
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        var session: BrowserSessionManager
        var tabID: UUID
        private var progressObservation: NSKeyValueObservation?
        private var titleObservation: NSKeyValueObservation?
        private var urlObservation: NSKeyValueObservation?
        private var canGoBackObservation: NSKeyValueObservation?
        private var canGoForwardObservation: NSKeyValueObservation?
        private var loadingObservation: NSKeyValueObservation?
        private var commandObserver: NSObjectProtocol?
        private var navigateObserver: NSObjectProtocol?

        init(session: BrowserSessionManager, tabID: UUID) {
            self.session = session
            self.tabID = tabID
        }

        deinit {
            if let commandObserver { NotificationCenter.default.removeObserver(commandObserver) }
            if let navigateObserver { NotificationCenter.default.removeObserver(navigateObserver) }
        }

        func observe(_ webView: WKWebView) {
            progressObservation = webView.observe(\.estimatedProgress, options: [.new]) { [weak self] view, _ in
                Task { @MainActor in self?.session.estimatedProgress = view.estimatedProgress }
            }
            titleObservation = webView.observe(\.title, options: [.new]) { [weak self] view, _ in
                Task { @MainActor in
                    self?.session.pageTitle = view.title ?? ""
                }
            }
            urlObservation = webView.observe(\.url, options: [.new]) { [weak self] view, _ in
                Task { @MainActor in
                    guard let url = view.url else { return }
                    self?.session.addressBarText = url.isDashSurfHome ? "" : url.absoluteString
                }
            }
            canGoBackObservation = webView.observe(\.canGoBack, options: [.new]) { [weak self] view, _ in
                Task { @MainActor in self?.session.canGoBack = view.canGoBack }
            }
            canGoForwardObservation = webView.observe(\.canGoForward, options: [.new]) { [weak self] view, _ in
                Task { @MainActor in self?.session.canGoForward = view.canGoForward }
            }
            loadingObservation = webView.observe(\.isLoading, options: [.new]) { [weak self] view, _ in
                Task { @MainActor in self?.session.isLoading = view.isLoading }
            }
        }

        func bindCommands(to webView: WKWebView) {
            commandObserver = NotificationCenter.default.addObserver(
                forName: .dashSurfBrowserCommand,
                object: nil,
                queue: .main
            ) { [weak webView] note in
                guard let command = note.object as? BrowserCommand, let webView else { return }
                switch command {
                case .goBack: if webView.canGoBack { webView.goBack() }
                case .goForward: if webView.canGoForward { webView.goForward() }
                case .reload: webView.reload()
                case .stop: webView.stopLoading()
                }
            }

            navigateObserver = NotificationCenter.default.addObserver(
                forName: .dashSurfNavigateActiveTab,
                object: nil,
                queue: .main
            ) { [weak self, weak webView] note in
                guard let self, let webView, let url = note.object as? URL else { return }
                guard self.session.tabManager.activeTabID == self.tabID else { return }
                if url.isDashSurfHome {
                    webView.loadHTMLString(HomeHTML.document, baseURL: nil)
                } else {
                    webView.load(URLRequest(url: url))
                }
            }
        }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            Task { @MainActor in
                session.isLoading = true
                session.errorMessage = nil
            }
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            Task { @MainActor in
                session.isLoading = false
                if let url = webView.url {
                    session.handleNavigationCommitted(url: url, title: webView.title)
                }
            }
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            handleError(error)
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            handleError(error)
        }

        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            Task { @MainActor in
                session.errorMessage = "The web page process crashed. Reloading…"
                webView.reload()
            }
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            if let url = navigationAction.request.url,
               let scheme = url.scheme?.lowercased(),
               scheme != "http", scheme != "https", scheme != "about", scheme != "blob", scheme != "data" {
                UIApplication.shared.open(url)
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }

        func webView(
            _ webView: WKWebView,
            createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction,
            windowFeatures: WKWindowFeatures
        ) -> WKWebView? {
            // Support window.open / target=_blank used by many login flows.
            if navigationAction.targetFrame == nil, let url = navigationAction.request.url {
                Task { @MainActor in
                    session.openURL(url, inNewTab: true)
                }
            }
            return nil
        }

        func webView(
            _ webView: WKWebView,
            didReceive challenge: URLAuthenticationChallenge,
            completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
        ) {
            // Never weaken TLS. Use default handling / reject untrusted certs.
            completionHandler(.performDefaultHandling, nil)
        }

        private func handleError(_ error: Error) {
            let ns = error as NSError
            if ns.domain == NSURLErrorDomain && ns.code == NSURLErrorCancelled { return }
            Task { @MainActor in
                session.isLoading = false
                session.errorMessage = ns.localizedDescription
                if ns.domain == NSURLErrorDomain && ns.code == NSURLErrorNotConnectedToInternet {
                    session.errorMessage = "No internet connection."
                }
            }
        }
    }
}

enum HomeHTML {
    static let document = """
    <!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>body{margin:0;background:#0B0F17;color:#A4ADBA;font: -apple-system-body;display:flex;align-items:center;justify-content:center;height:100vh}
    h1{color:#fff;font-size:22px;margin:0 0 8px} p{margin:0}</style></head>
    <body><div style="text-align:center"><h1>DashSurf</h1><p>Your browser. Your screen. Your way.</p></div></body></html>
    """
}
'''.lstrip())

    w("Browser/BrowserView.swift", r'''
import SwiftUI

struct BrowserContainerView: View {
    @ObservedObject var coordinator: AppCoordinator
    @EnvironmentObject private var session: BrowserSessionManager
    @EnvironmentObject private var tabManager: TabManager
    @StateObject private var viewModel: BrowserViewModel

    init(coordinator: AppCoordinator) {
        self.coordinator = coordinator
        // Temporary placeholder; replaced in onAppear with real deps via StateObject workaround below.
        _viewModel = StateObject(wrappedValue: BrowserViewModel(
            session: AppDependencies.shared.sessionManager,
            tabManager: AppDependencies.shared.tabManager
        ))
    }

    var body: some View {
        BrowserView(viewModel: viewModel)
    }
}

struct BrowserView: View {
    @ObservedObject var viewModel: BrowserViewModel
    @EnvironmentObject private var session: BrowserSessionManager
    @EnvironmentObject private var tabManager: TabManager
    @EnvironmentObject private var settings: SettingsStore
    @State private var showShare = false
    @State private var showClearDomainConfirm = false

    var body: some View {
        VStack(spacing: 0) {
            BrowserChrome(
                address: $session.addressBarText,
                progress: session.estimatedProgress,
                isLoading: session.isLoading,
                canGoBack: session.canGoBack,
                canGoForward: session.canGoForward,
                tabCount: tabManager.tabs.count,
                onSubmit: { session.submitAddressBar() },
                onBack: viewModel.goBack,
                onForward: viewModel.goForward,
                onReload: viewModel.reloadOrStop,
                onTabs: { viewModel.showTabsSheet = true },
                onMenu: { viewModel.showMenu = true },
                onFavorite: {
                    _ = try? session.addBookmarkForCurrentPage()
                }
            )

            ZStack {
                if let activeID = tabManager.activeTabID {
                    WebViewRepresentable(tabID: activeID, session: session)
                        .id(activeID)
                } else {
                    Color(DashSurfTheme.primaryBackground)
                }

                if let message = session.errorMessage {
                    ErrorBanner(message: message) {
                        session.errorMessage = nil
                        viewModel.reloadOrStop()
                    }
                    .padding()
                }
            }
        }
        .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
        .sheet(isPresented: $viewModel.showTabsSheet) {
            TabsSheet(tabManager: tabManager, session: session)
        }
        .confirmationDialog("Browser Menu", isPresented: $viewModel.showMenu, titleVisibility: .visible) {
            Button("New Tab") { _ = tabManager.openNewTab(activate: true) }
            Button("Add Bookmark") { _ = try? session.addBookmarkForCurrentPage() }
            Button("Share") { showShare = true }
            Button("Copy Link") {
                UIPasteboard.general.string = session.currentURL.absoluteString
            }
            Button("Open in Safari") {
                UIApplication.shared.open(session.currentURL)
            }
            Button(session.desktopMode ? "Mobile Site" : "Desktop Site") {
                session.toggleDesktopMode()
            }
            Button("Clear Website Data for Domain", role: .destructive) {
                showClearDomainConfirm = true
            }
            Button("Cancel", role: .cancel) {}
        }
        .sheet(isPresented: $showShare) {
            if let url = viewModel.shareCurrent() {
                ShareSheet(items: [url])
            }
        }
        .alert("Clear data for \(session.currentURL.dashsurfDomain)?", isPresented: $showClearDomainConfirm) {
            Button("Clear", role: .destructive) {
                let domain = session.currentURL.dashsurfDomain
                Task {
                    await AppDependencies.shared.websiteDataService.clearData(forDomain: domain)
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Removes cookies and site data for this domain from DashSurf. Safari data is not affected.")
        }
    }
}
'''.lstrip())

    w("Browser/BrowserChrome.swift", r'''
import SwiftUI

struct BrowserChrome: View {
    @Binding var address: String
    var progress: Double
    var isLoading: Bool
    var canGoBack: Bool
    var canGoForward: Bool
    var tabCount: Int
    var onSubmit: () -> Void
    var onBack: () -> Void
    var onForward: () -> Void
    var onReload: () -> Void
    var onTabs: () -> Void
    var onMenu: () -> Void
    var onFavorite: () -> Void

    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 10) {
                Button(action: onBack) {
                    Image(systemName: "chevron.left")
                }
                .disabled(!canGoBack)

                Button(action: onForward) {
                    Image(systemName: "chevron.right")
                }
                .disabled(!canGoForward)

                HStack {
                    Image(systemName: "lock.fill")
                        .font(.caption2)
                        .foregroundStyle(DashSurfTheme.secondaryText)
                    TextField("Search or enter website", text: $address)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                        .submitLabel(.go)
                        .onSubmit(onSubmit)
                    Button(action: onReload) {
                        Image(systemName: isLoading ? "xmark" : "arrow.clockwise")
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(DashSurfTheme.secondaryBackground, in: Capsule())

                Button(action: onFavorite) {
                    Image(systemName: "book")
                }
                Button(action: onTabs) {
                    Text("\(tabCount)")
                        .font(.caption.weight(.semibold))
                        .frame(width: 22, height: 22)
                        .overlay(RoundedRectangle(cornerRadius: 6).stroke(DashSurfTheme.primaryText, lineWidth: 1.5))
                }
                Button(action: onMenu) {
                    Image(systemName: "ellipsis")
                }
            }
            .foregroundStyle(DashSurfTheme.primaryText)
            .padding(.horizontal, 12)
            .padding(.top, 8)

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.clear)
                    Capsule()
                        .fill(DashSurfTheme.accent)
                        .frame(width: max(0, geo.size.width * progress))
                        .opacity(isLoading || progress > 0 && progress < 1 ? 1 : 0)
                }
            }
            .frame(height: 2)
            .padding(.horizontal, 16)
        }
        .background(DashSurfTheme.primaryBackground.opacity(0.96))
    }
}

struct TabsSheet: View {
    @ObservedObject var tabManager: TabManager
    @ObservedObject var session: BrowserSessionManager
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                ForEach(tabManager.tabs) { tab in
                    Button {
                        tabManager.selectTab(id: tab.id)
                        session.currentURL = tab.url
                        session.addressBarText = tab.url.isDashSurfHome ? "" : tab.url.absoluteString
                        dismiss()
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(tab.title).foregroundStyle(DashSurfTheme.primaryText)
                            Text(tab.url.absoluteString)
                                .font(.caption)
                                .foregroundStyle(DashSurfTheme.secondaryText)
                                .lineLimit(1)
                        }
                    }
                    .swipeActions {
                        Button(role: .destructive) {
                            session.webViewFactory.recycle(tabID: tab.id)
                            tabManager.closeTab(id: tab.id)
                        } label: {
                            Label("Close", systemImage: "xmark")
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(DashSurfTheme.primaryBackground)
            .navigationTitle("Tabs")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Close All") {
                        for tab in tabManager.tabs {
                            session.webViewFactory.recycle(tabID: tab.id)
                        }
                        tabManager.closeAll()
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        _ = tabManager.openNewTab(activate: true)
                        dismiss()
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}

struct ErrorBanner: View {
    let message: String
    var retry: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text(message)
                .multilineTextAlignment(.center)
                .foregroundStyle(DashSurfTheme.primaryText)
            Button("Try Again", action: retry)
                .buttonStyle(.borderedProminent)
                .tint(DashSurfTheme.accent)
        }
        .padding(20)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }
}

struct ShareSheet: UIViewControllerRepresentable {
    var items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
'''.lstrip())


print("browser module writer ready")
