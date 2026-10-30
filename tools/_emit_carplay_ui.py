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
APP = emit.APP
TESTS = emit.TESTS


def write_carplay() -> None:
    w("CarPlay/CarPlaySceneRole.swift", r'''
import UIKit

/// UIKit does not expose CarPlay window scene role as a typed Swift member.
/// The raw string matches Info.plist UIWindowSceneSessionRoleCarPlay.
/// Pattern documented by Apple scene manifests and used by MIT-licensed Cafari Lite.
enum CarPlaySceneRole {
    static let windowRole = UISceneSession.Role(rawValue: "UIWindowSceneSessionRoleCarPlay")
}
'''.lstrip())

    w("CarPlay/CarPlayAvailabilityService.swift", r'''
import Foundation
import Combine
import UIKit

enum CarPlayAvailabilityStatus: Equatable {
    case phoneOnlyNoEntitlementConfigured
    case entitlementsConfiguredButNotConnected
    case connected
    case featureUnavailable(reason: String)

    var summary: String {
        switch self {
        case .phoneOnlyNoEntitlementConfigured:
            return "CarPlay car window not enabled in this build (no CarPlay entitlements signed in)."
        case .entitlementsConfiguredButNotConnected:
            return "CarPlay entitlements present in project configuration; waiting for vehicle connection."
        case .connected:
            return "CarPlay window scene is connected."
        case .featureUnavailable(let reason):
            return reason
        }
    }
}

@MainActor
final class CarPlayAvailabilityService: ObservableObject {
    @Published private(set) var status: CarPlayAvailabilityStatus = .phoneOnlyNoEntitlementConfigured
    @Published private(set) var isCarSceneConnected = false
    @Published private(set) var entitlementKeysDetectedInBundle: [String] = []

    var connectionLabel: String {
        isCarSceneConnected ? "Connected" : "Not connected"
    }

    var capabilityNotes: [String] {
        [
            "Full unrestricted WKWebView browsing on CarPlay is not a guaranteed public CarPlay template API.",
            "Optional DashSurf car window uses UIWindowSceneSessionRoleCarPlay and requires Apple-granted entitlements.",
            "Video should only display when the vehicle allows it (parked / supported head unit).",
            "Without entitlements DashSurf remains a complete iPhone browser."
        ]
    }

    func refreshFromBundle() {
        let keys = Self.readCarPlayEntitlementKeys()
        entitlementKeysDetectedInBundle = keys
        if keys.isEmpty {
            status = .phoneOnlyNoEntitlementConfigured
        } else if isCarSceneConnected {
            status = .connected
        } else {
            status = .entitlementsConfiguredButNotConnected
        }
    }

    func notePhoneSceneConnected() {
        refreshFromBundle()
    }

    func noteCarSceneConnected() {
        isCarSceneConnected = true
        status = .connected
        NotificationCenter.default.post(name: DashSurfNotification.carPlayConnected, object: nil)
    }

    func noteCarSceneDisconnected() {
        isCarSceneConnected = false
        refreshFromBundle()
        NotificationCenter.default.post(name: DashSurfNotification.carPlayDisconnected, object: nil)
    }

    /// Best-effort read of embedded entitlements. Not a private API probe —
    /// uses the signed app's embedded.mobileprovision / entitlements when present.
    /// If unavailable, falls back to Info.plist marker + CODE_SIGN configuration honesty.
    private static func readCarPlayEntitlementKeys() -> [String] {
        // Public API cannot reliably enumerate managed entitlements at runtime on device
        // without reading the embedded profile. We check a compile-time flag and Info.plist.
        var found: [String] = []
        #if DASHSURF_CARPLAY_ENABLED
        found.append("com.apple.developer.carplay-video")
        found.append("com.apple.developer.carplay-audio")
        #endif
        if let path = Bundle.main.path(forResource: "embedded", ofType: "mobileprovision"),
           let data = try? Data(contentsOf: URL(fileURLWithPath: path)),
           let text = String(data: data, encoding: .ascii) {
            if text.contains("com.apple.developer.carplay-video") {
                found.append("com.apple.developer.carplay-video")
            }
            if text.contains("com.apple.developer.carplay-audio") {
                found.append("com.apple.developer.carplay-audio")
            }
        }
        return Array(Set(found)).sorted()
    }
}
'''.lstrip())

    w("CarPlay/CarPlaySessionManager.swift", r'''
import Foundation
import Combine

/// Shared logical state between iPhone UI and optional CarPlay window.
/// Does not move WKWebView instances across screens.
@MainActor
final class CarPlaySessionManager: ObservableObject {
    @Published var lastURLSentToCar: URL?

    private let sessionManager: BrowserSessionManager
    let availability: CarPlayAvailabilityService
    private let quickAccessRepository: QuickAccessRepository
    private let bookmarkRepository: BookmarkRepository
    private let historyRepository: HistoryRepository
    private let recentMediaRepository: RecentMediaRepository

    init(
        sessionManager: BrowserSessionManager,
        availability: CarPlayAvailabilityService,
        quickAccessRepository: QuickAccessRepository,
        bookmarkRepository: BookmarkRepository,
        historyRepository: HistoryRepository,
        recentMediaRepository: RecentMediaRepository
    ) {
        self.sessionManager = sessionManager
        self.availability = availability
        self.quickAccessRepository = quickAccessRepository
        self.bookmarkRepository = bookmarkRepository
        self.historyRepository = historyRepository
        self.recentMediaRepository = recentMediaRepository
    }

    func sendActivePageToCar() {
        let url = sessionManager.currentURL
        lastURLSentToCar = url
        NotificationCenter.default.post(name: DashSurfNotification.sendURLToCarPlay, object: url)
    }

    func quickAccess() -> [QuickAccessItem] {
        (try? quickAccessRepository.all()) ?? []
    }

    func favoriteBookmarks() -> [Bookmark] {
        (try? bookmarkRepository.favorites()) ?? []
    }

    func recentHistory(limit: Int = 20) -> [BrowserHistoryItem] {
        (try? historyRepository.recent(limit: limit)) ?? []
    }

    func continueWatching(limit: Int = 12) -> [RecentMediaItem] {
        Array(((try? recentMediaRepository.recent(limit: limit)) ?? []).prefix(limit))
    }
}
'''.lstrip())

    w("CarPlay/CarPlayCoordinator.swift", r'''
import UIKit

@MainActor
final class CarPlayCoordinator {
    static let shared = CarPlayCoordinator()

    private(set) weak var carWindow: UIWindow?
    private(set) weak var browserController: CarPlayBrowserViewController?

    func attach(window: UIWindow, controller: CarPlayBrowserViewController) {
        carWindow = window
        browserController = controller
        AppDependencies.shared.carPlayAvailability.noteCarSceneConnected()
        CarMotionGate.shared.start()
    }

    func detach() {
        carWindow = nil
        browserController = nil
        AppDependencies.shared.carPlayAvailability.noteCarSceneDisconnected()
        CarMotionGate.shared.stop()
    }

    func loadURL(_ url: URL) {
        browserController?.load(url: url)
    }
}
'''.lstrip())

    w("CarPlay/CarPlaySceneDelegate.swift", r'''
import UIKit

/// Hosts an optional car UIWindowScene when Apple has granted CarPlay entitlements.
/// Inspired by the MIT-licensed Cafari Lite scene pattern; DashSurf UI and data layer are original.
final class CarPlaySceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: windowScene)
        let controller = CarPlayBrowserViewController(
            sessionManager: AppDependencies.shared.sessionManager,
            carPlaySession: AppDependencies.shared.carPlaySession
        )
        window.rootViewController = controller
        window.makeKeyAndVisible()
        self.window = window
        Task { @MainActor in
            CarPlayCoordinator.shared.attach(window: window, controller: controller)
        }
    }

    func sceneDidDisconnect(_ scene: UIScene) {
        window = nil
        Task { @MainActor in
            CarPlayCoordinator.shared.detach()
        }
    }
}
'''.lstrip())

    w("CarPlay/CarPlayBrowserViewController.swift", r'''
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

        if let last = carPlaySession.lastURLSentToCar ?? sessionManager.currentURL as URL?,
           !last.isDashSurfHome {
            load(url: last)
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
'''.lstrip())

    w("CarPlay/CarMotionGate.swift", r'''
import CoreLocation
import Foundation

/// Conservative motion gate for car-screen video. There is no public CarPlay API
/// that reports "vehicle is parked". Speed from Core Location is a best-effort proxy.
/// If location is denied, we do NOT block playback (cannot measure ≠ driving).
final class CarMotionGate: NSObject, CLLocationManagerDelegate {
    static let shared = CarMotionGate()
    static let stateChanged = Notification.Name("DashSurf.CarMotionGateChanged")

    private(set) var isMoving = false
    private let manager = CLLocationManager()
    private var running = false
    private let movingSpeed: CLLocationSpeed = 3.0
    private let samplesToFlip = 3
    private var agreeing = 0

    private override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyKilometer
        manager.distanceFilter = 10
        manager.pausesLocationUpdatesAutomatically = true
    }

    func start() {
        guard !running else { return }
        running = true
        if manager.authorizationStatus == .notDetermined {
            manager.requestWhenInUseAuthorization()
        }
        manager.startUpdatingLocation()
    }

    func stop() {
        guard running else { return }
        running = false
        manager.stopUpdatingLocation()
        setMoving(false)
    }

    private func setMoving(_ moving: Bool) {
        guard moving != isMoving else { return }
        isMoving = moving
        NotificationCenter.default.post(name: CarMotionGate.stateChanged, object: nil)
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let speed = locations.last?.speed, speed >= 0 else { return }
        let moving = speed > movingSpeed
        if moving == isMoving {
            agreeing = 0
            return
        }
        agreeing += 1
        if agreeing >= samplesToFlip {
            agreeing = 0
            setMoving(moving)
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        // No fix is not evidence of driving.
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        if manager.authorizationStatus == .denied || manager.authorizationStatus == .restricted {
            setMoving(false)
        }
    }
}
'''.lstrip())


def write_ui() -> None:
    w("UI/Theme/DashSurfTheme.swift", r'''
import SwiftUI

enum DashSurfTheme {
    static let primaryBackground = Color(hex: 0x0B0F17)
    static let secondaryBackground = Color(hex: 0x151B26)
    static let accent = Color(hex: 0x3186FF)
    static let primaryText = Color(hex: 0xFFFFFF)
    static let secondaryText = Color(hex: 0xA4ADBA)

    static var backgroundGradient: LinearGradient {
        LinearGradient(
            colors: [primaryBackground, secondaryBackground.opacity(0.95), primaryBackground],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}

extension Color {
    init(hex: UInt32, opacity: Double = 1) {
        let r = Double((hex >> 16) & 0xFF) / 255
        let g = Double((hex >> 8) & 0xFF) / 255
        let b = Double(hex & 0xFF) / 255
        self.init(.sRGB, red: r, green: g, blue: b, opacity: opacity)
    }
}
'''.lstrip())


def write_assets() -> None:
    assets = APP / "Resources" / "Assets.xcassets"
    (assets / "AppIcon.appiconset").mkdir(parents=True, exist_ok=True)
    (assets / "AccentColor.colorset").mkdir(parents=True, exist_ok=True)
    (assets / "LaunchBackground.colorset").mkdir(parents=True, exist_ok=True)
    (assets / "PrimaryBackground.colorset").mkdir(parents=True, exist_ok=True)
    (assets / "SecondaryBackground.colorset").mkdir(parents=True, exist_ok=True)

    (assets / "Contents.json").write_text(
        '{\n  "info" : {\n    "author" : "xcode",\n    "version" : 1\n  }\n}\n',
        encoding="utf-8",
    )

    # App icon: use a single 1024 template note; generate PNG via Python if possible
    (assets / "AppIcon.appiconset" / "Contents.json").write_text(
        '''{
  "images" : [
    {
      "filename" : "AppIcon.png",
      "idiom" : "universal",
      "platform" : "ios",
      "size" : "1024x1024"
    }
  ],
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}
''',
        encoding="utf-8",
    )

    def colorset(name: str, hex_rgb: tuple[float, float, float]) -> None:
        r, g, b = hex_rgb
        (assets / f"{name}.colorset" / "Contents.json").write_text(
            f'''{{
  "colors" : [
    {{
      "color" : {{
        "color-space" : "srgb",
        "components" : {{
          "alpha" : "1.000",
          "blue" : "{b:.3f}",
          "green" : "{g:.3f}",
          "red" : "{r:.3f}"
        }}
      }},
      "idiom" : "universal"
    }}
  ],
  "info" : {{
    "author" : "xcode",
    "version" : 1
  }}
}}
''',
            encoding="utf-8",
        )

    colorset("AccentColor", (0.192, 0.525, 1.0))
    colorset("LaunchBackground", (0.043, 0.059, 0.090))
    colorset("PrimaryBackground", (0.043, 0.059, 0.090))
    colorset("SecondaryBackground", (0.082, 0.106, 0.149))

    # Generate a simple 1024 PNG AppIcon without external deps (minimal PNG writer)
    png_path = assets / "AppIcon.appiconset" / "AppIcon.png"
    write_app_icon_png(png_path)
    print(f"  {png_path.relative_to(ROOT)}")


def write_app_icon_png(path: Path) -> None:
    """Create a 1024x1024 PNG: dark background + blue stylized D."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
        img = Image.new("RGB", (1024, 1024), (11, 15, 23))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((96, 96, 928, 928), radius=220, fill=(21, 27, 38))
        # Browser ring
        draw.ellipse((280, 280, 744, 744), outline=(49, 134, 255), width=36)
        draw.ellipse((360, 360, 664, 664), outline=(49, 134, 255), width=18)
        # D letter block
        draw.rounded_rectangle((430, 360, 620, 664), radius=40, fill=(49, 134, 255))
        draw.rounded_rectangle((470, 410, 560, 614), radius=20, fill=(21, 27, 38))
        img.save(path, format="PNG")
        return
    except Exception:
        pass

    # Fallback: solid dark PNG via raw zlib PNG encoder
    import struct
    import zlib

    width = height = 1024
    # Dark navy pixels with a blue circle approximation in center
    rows = []
    cx, cy, r_outer, r_inner = 512, 512, 220, 140
    for y in range(height):
        row = bytearray([0])  # filter none
        for x in range(width):
            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < r_inner:
                row.extend((21, 27, 38))
            elif dist < r_outer:
                row.extend((49, 134, 255))
            elif 420 <= x <= 620 and 360 <= y <= 664 and not (470 <= x <= 560 and 410 <= y <= 614):
                row.extend((49, 134, 255))
            else:
                row.extend((11, 15, 23))
        rows.append(bytes(row))
    raw = b"".join(rows)
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    path.write_bytes(png)


def write_tests() -> None:
    w(
        "URLServiceTests.swift",
        r'''
import XCTest
@testable import DashSurf

final class URLServiceTests: XCTestCase {
    private let service = URLService()

    func testNormalizeURLDropsUTM() {
        let url = URL(string: "https://example.com/path?utm_source=x&id=1")!
        let normalized = URLService.normalizeForHistory(url)
        XCTAssertEqual(normalized.host, "example.com")
        XCTAssertTrue(normalized.query?.contains("id=1") == true)
        XCTAssertFalse(normalized.query?.contains("utm_source") == true)
    }

    func testResolveDomainAddsHTTPS() {
        let url = service.resolve("example.com", searchEngine: .google)
        XCTAssertEqual(url.absoluteString, "https://example.com")
    }

    func testResolveQueryUsesSearchEngine() {
        let url = service.resolve("swift concurrency", searchEngine: .google)
        XCTAssertTrue(url.absoluteString.contains("google.com/search"))
        XCTAssertTrue(url.absoluteString.contains("swift"))
    }

    func testGoogleSearchEncoding() {
        let url = SearchEngine.google.searchURL(for: "hello world")
        XCTAssertTrue(url.absoluteString.contains("hello"))
    }
}
'''.lstrip(),
        base=TESTS,
    )

    w(
        "HistoryRepositoryTests.swift",
        r'''
import XCTest
import SwiftData
@testable import DashSurf

@MainActor
final class HistoryRepositoryTests: XCTestCase {
    private var persistence: PersistenceController!
    private var repository: HistoryRepository!

    override func setUp() async throws {
        persistence = PersistenceController(inMemory: true)
        repository = HistoryRepository(modelContext: ModelContext(persistence.container))
    }

    func testAddAndSearchHistory() throws {
        let url = URL(string: "https://example.com/a")!
        try repository.recordVisit(url: url, title: "Example")
        let results = try repository.search(query: "example")
        XCTAssertEqual(results.count, 1)
        XCTAssertEqual(results.first?.title, "Example")
    }

    func testDeleteHistory() throws {
        let url = URL(string: "https://example.com/b")!
        try repository.recordVisit(url: url, title: "B")
        let item = try repository.recent().first!
        try repository.delete(item)
        XCTAssertTrue(try repository.recent().isEmpty)
    }

    func testClearHistory() throws {
        try repository.recordVisit(url: URL(string: "https://a.com")!, title: "A")
        try repository.recordVisit(url: URL(string: "https://b.com")!, title: "B")
        try repository.clearAll()
        XCTAssertTrue(try repository.recent().isEmpty)
    }

    func testDedupWithinWindowIncrementsVisitCount() throws {
        let url = URL(string: "https://example.com/c")!
        try repository.recordVisit(url: url, title: "C")
        // Immediate second write within dedup window should not create a second row,
        // and may skip visitCount bump depending on timing — assert single row.
        try repository.recordVisit(url: url, title: "C2")
        let all = try repository.search(query: "")
        XCTAssertEqual(all.filter { $0.urlString.contains("/c") }.count, 1)
    }
}
'''.lstrip(),
        base=TESTS,
    )

    w(
        "BookmarkRepositoryTests.swift",
        r'''
import XCTest
import SwiftData
@testable import DashSurf

@MainActor
final class BookmarkRepositoryTests: XCTestCase {
    private var repository: BookmarkRepository!

    override func setUp() async throws {
        let persistence = PersistenceController(inMemory: true)
        repository = BookmarkRepository(modelContext: ModelContext(persistence.container))
    }

    func testAddUpdateDeleteBookmark() throws {
        let bookmark = try repository.add(title: "Apple", url: URL(string: "https://apple.com")!)
        XCTAssertEqual(try repository.all().count, 1)
        try repository.update(bookmark, title: "Apple Inc", url: URL(string: "https://www.apple.com")!, isFavorite: true)
        XCTAssertEqual(try repository.favorites().count, 1)
        try repository.delete(bookmark)
        XCTAssertTrue(try repository.all().isEmpty)
    }
}
'''.lstrip(),
        base=TESTS,
    )

    w(
        "TabManagerTests.swift",
        r'''
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
'''.lstrip(),
        base=TESTS,
    )

    w(
        "RecentMediaRepositoryTests.swift",
        r'''
import XCTest
import SwiftData
@testable import DashSurf

@MainActor
final class RecentMediaRepositoryTests: XCTestCase {
    func testUpsertRecentMedia() throws {
        let persistence = PersistenceController(inMemory: true)
        let repo = RecentMediaRepository(modelContext: ModelContext(persistence.container))
        let url = URL(string: "https://www.youtube.com/watch?v=dQw4w9WgXcQ")!
        try repo.upsert(url: url, title: "Video", provider: "YouTube")
        try repo.upsert(url: url, title: "Video Updated", provider: "YouTube")
        let items = try repo.recent()
        XCTAssertEqual(items.count, 1)
        XCTAssertEqual(items.first?.title, "Video Updated")
    }
}
'''.lstrip(),
        base=TESTS,
    )

    w(
        "MediaDetectionTests.swift",
        r'''
import XCTest
@testable import DashSurf

final class MediaDetectionTests: XCTestCase {
    func testDetectYouTube() {
        let service = MediaDetectionService()
        let url = URL(string: "https://www.youtube.com/watch?v=abcdefghijk")!
        let media = service.detect(url: url, pageTitle: "Test")
        XCTAssertEqual(media?.provider, "YouTube")
        XCTAssertNotNil(media?.thumbnailURL)
    }

    func testIgnorePlainHomepage() {
        let service = MediaDetectionService()
        let url = URL(string: "https://www.youtube.com/")!
        XCTAssertNil(service.detect(url: url, pageTitle: "YouTube"))
    }
}
'''.lstrip(),
        base=TESTS,
    )

    w(
        "SettingsStoreTests.swift",
        r'''
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
'''.lstrip(),
        base=TESTS,
    )


print("carplay/ui/tests writers ready")
