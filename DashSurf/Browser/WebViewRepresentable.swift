import SwiftUI
import UIKit
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
