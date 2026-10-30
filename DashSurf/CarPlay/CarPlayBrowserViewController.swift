import UIKit
import WebKit

/// Minimal chrome browser for the car window. Separate WKWebView instance;
/// shares WKWebsiteDataStore.default() with the phone for cookies/localStorage.
@MainActor
final class CarPlayBrowserViewController: UIViewController, WKNavigationDelegate, WKUIDelegate {
    private let sessionManager: BrowserSessionManager
    private let carPlaySession: CarPlaySessionManager
    private var webView: WKWebView!
    private let overlay = UIVisualEffectView(effect: UIBlurEffect(style: .systemUltraThinMaterialDark))
    private let blockedLabel = UILabel()
    private var sendObserver: NSObjectProtocol?
    private var gateObserver: NSObjectProtocol?

    init(sessionManager: BrowserSessionManager, carPlaySession: CarPlaySessionManager) {
        self.sessionManager = sessionManager
        self.carPlaySession = carPlaySession
        super.init(nibName: nil, bundle: nil)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(DashSurfTheme.primaryBackground)

        let config = AppDependencies.shared.websiteDataService.makeConfiguration(desktopMode: false)
        webView = WKWebView(frame: view.bounds, configuration: config)
        webView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        view.addSubview(webView)

        setupLauncher()
        setupMotionOverlay()
        observe()

        let candidate = carPlaySession.lastURLSentToCar ?? sessionManager.currentURL
        if !candidate.isDashSurfHome {
            load(url: candidate)
        } else if let first = carPlaySession.quickAccess().first?.url {
            load(url: first)
        } else {
            load(url: URL(string: "https://m.youtube.com")!)
        }
    }

    deinit {
        if let sendObserver { NotificationCenter.default.removeObserver(sendObserver) }
        if let gateObserver { NotificationCenter.default.removeObserver(gateObserver) }
    }

    func load(url: URL) {
        webView.load(URLRequest(url: url))
    }

    private func setupLauncher() {
        let stack = UIStackView()
        stack.axis = .horizontal
        stack.spacing = 8
        stack.translatesAutoresizingMaskIntoConstraints = false

        let buttons: [(String, () -> Void)] = [
            ("Shortcuts", { [weak self] in self?.showQuickList() }),
            ("Watching", { [weak self] in self?.showContinueWatching() }),
            ("Reload", { [weak self] in self?.webView.reload() })
        ]
        for (title, action) in buttons {
            let button = UIButton(type: .system)
            button.setTitle(title, for: .normal)
            button.tintColor = UIColor(DashSurfTheme.accent)
            button.backgroundColor = UIColor.black.withAlphaComponent(0.45)
            button.layer.cornerRadius = 10
            button.contentEdgeInsets = UIEdgeInsets(top: 8, left: 12, bottom: 8, right: 12)
            button.addAction(UIAction { _ in action() }, for: .touchUpInside)
            stack.addArrangedSubview(button)
        }
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 12),
            stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 8)
        ])
    }

    private func setupMotionOverlay() {
        overlay.translatesAutoresizingMaskIntoConstraints = false
        overlay.isHidden = true
        blockedLabel.text = "Video paused while driving.\nPark to continue."
        blockedLabel.textAlignment = .center
        blockedLabel.textColor = .white
        blockedLabel.numberOfLines = 0
        blockedLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(overlay)
        overlay.contentView.addSubview(blockedLabel)
        NSLayoutConstraint.activate([
            overlay.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            overlay.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            overlay.topAnchor.constraint(equalTo: view.topAnchor),
            overlay.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            blockedLabel.centerXAnchor.constraint(equalTo: overlay.contentView.centerXAnchor),
            blockedLabel.centerYAnchor.constraint(equalTo: overlay.contentView.centerYAnchor),
            blockedLabel.leadingAnchor.constraint(greaterThanOrEqualTo: overlay.contentView.leadingAnchor, constant: 24)
        ])
    }

    private func observe() {
        sendObserver = NotificationCenter.default.addObserver(
            forName: DashSurfNotification.sendURLToCarPlay,
            object: nil,
            queue: .main
        ) { [weak self] note in
            if let url = note.object as? URL {
                Task { @MainActor in self?.load(url: url) }
            }
        }
        gateObserver = NotificationCenter.default.addObserver(
            forName: CarMotionGate.stateChanged,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in self?.applyGate() }
        }
        applyGate()
    }

    private func applyGate() {
        let moving = CarMotionGate.shared.isMoving
        overlay.isHidden = !moving
        if moving {
            webView.evaluateJavaScript("document.querySelectorAll('video').forEach(v => v.pause());", completionHandler: nil)
        }
    }

    private func showQuickList() {
        let items = carPlaySession.quickAccess()
        presentList(title: "Quick Access", titles: items.map(\.title)) { [weak self] index in
            if let url = items[index].url { self?.load(url: url) }
        }
    }

    private func showContinueWatching() {
        let items = carPlaySession.continueWatching()
        presentList(title: "Continue Watching", titles: items.map(\.title)) { [weak self] index in
            if let url = items[index].url { self?.load(url: url) }
        }
    }

    private func presentList(title: String, titles: [String], pick: @escaping (Int) -> Void) {
        let alert = UIAlertController(title: title, message: nil, preferredStyle: .actionSheet)
        for (index, name) in titles.enumerated() {
            alert.addAction(UIAlertAction(title: name, style: .default) { _ in pick(index) })
        }
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel))
        if let pop = alert.popoverPresentationController {
            pop.sourceView = view
            pop.sourceRect = CGRect(x: 40, y: 80, width: 1, height: 1)
        }
        present(alert, animated: true)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if let url = webView.url {
            sessionManager.handleNavigationCommitted(url: url, title: webView.title)
        }
    }

    func webView(
        _ webView: WKWebView,
        createWebViewWith configuration: WKWebViewConfiguration,
        for navigationAction: WKNavigationAction,
        windowFeatures: WKWindowFeatures
    ) -> WKWebView? {
        if let url = navigationAction.request.url {
            load(url: url)
        }
        return nil
    }
}
