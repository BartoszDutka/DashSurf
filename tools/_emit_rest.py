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


def write_persistence() -> None:
    w("Persistence/PersistenceController.swift", r'''
import Foundation
import SwiftData

@MainActor
final class PersistenceController {
    let container: ModelContainer

    init(inMemory: Bool = false) {
        let schema = Schema([
            BrowserHistoryItem.self,
            Bookmark.self,
            BookmarkFolder.self,
            RecentMediaItem.self,
            QuickAccessItem.self,
            BrowserTabRecord.self
        ])
        let config = ModelConfiguration(
            "DashSurf",
            schema: schema,
            isStoredInMemoryOnly: inMemory
        )
        do {
            container = try ModelContainer(for: schema, configurations: [config])
        } catch {
            fatalError("DashSurf failed to create ModelContainer: \(error)")
        }
    }

    static func makeShared() -> PersistenceController {
        PersistenceController(inMemory: false)
    }

    static func makePreview() -> PersistenceController {
        PersistenceController(inMemory: true)
    }
}
'''.lstrip())

    w("Persistence/HistoryRepository.swift", r'''
import Foundation
import SwiftData

@MainActor
final class HistoryRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func recordVisit(url: URL, title: String?, faviconURL: URL? = nil) throws {
        guard !url.isDashSurfHome else { return }
        guard url.scheme == "http" || url.scheme == "https" else { return }

        let normalized = URLService.normalizeForHistory(url)
        let urlString = normalized.absoluteString
        let domain = normalized.dashsurfDomain
        let now = Date()

        var descriptor = FetchDescriptor<BrowserHistoryItem>(
            predicate: #Predicate { $0.urlString == urlString },
            sortBy: [SortDescriptor(\.lastVisitedAt, order: .reverse)]
        )
        descriptor.fetchLimit = 1
        if let existing = try modelContext.fetch(descriptor).first {
            if now.timeIntervalSince(existing.lastVisitedAt) < AppConstants.historyDedupWindow {
                if let title, !title.isEmpty { existing.title = title }
                return
            }
            existing.visitCount += 1
            existing.lastVisitedAt = now
            if let title, !title.isEmpty { existing.title = title }
            if let faviconURL { existing.faviconURLString = faviconURL.absoluteString }
        } else {
            let item = BrowserHistoryItem(
                urlString: urlString,
                title: (title?.nilIfEmpty) ?? domain,
                domain: domain,
                faviconURLString: faviconURL?.absoluteString,
                firstVisitedAt: now,
                lastVisitedAt: now,
                visitCount: 1
            )
            modelContext.insert(item)
        }
        try modelContext.save()
    }

    func search(query: String, limit: Int = 200) throws -> [BrowserHistoryItem] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        var descriptor = FetchDescriptor<BrowserHistoryItem>(
            sortBy: [SortDescriptor(\.lastVisitedAt, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        let all = try modelContext.fetch(descriptor)
        guard !q.isEmpty else { return all }
        let lowered = q.lowercased()
        return all.filter {
            $0.title.lowercased().contains(lowered)
                || $0.urlString.lowercased().contains(lowered)
                || $0.domain.lowercased().contains(lowered)
        }
    }

    func recent(limit: Int = 20) throws -> [BrowserHistoryItem] {
        var descriptor = FetchDescriptor<BrowserHistoryItem>(
            sortBy: [SortDescriptor(\.lastVisitedAt, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        return try modelContext.fetch(descriptor)
    }

    func items(forDomain domain: String) throws -> [BrowserHistoryItem] {
        let d = domain.lowercased()
        let descriptor = FetchDescriptor<BrowserHistoryItem>(
            predicate: #Predicate { $0.domain == d },
            sortBy: [SortDescriptor(\.lastVisitedAt, order: .reverse)]
        )
        return try modelContext.fetch(descriptor)
    }

    func delete(_ item: BrowserHistoryItem) throws {
        modelContext.delete(item)
        try modelContext.save()
    }

    func deleteDomain(_ domain: String) throws {
        for item in try items(forDomain: domain) {
            modelContext.delete(item)
        }
        try modelContext.save()
    }

    func clearAll() throws {
        try modelContext.delete(model: BrowserHistoryItem.self)
        try modelContext.save()
    }

    func grouped(query: String = "") throws -> [(HistoryDateGroup, [BrowserHistoryItem])] {
        let items = try search(query: query, limit: 2000)
        var buckets: [HistoryDateGroup: [BrowserHistoryItem]] = [:]
        for item in items {
            let g = HistoryDateGroup.group(for: item.lastVisitedAt)
            buckets[g, default: []].append(item)
        }
        return HistoryDateGroup.allCases.compactMap { g in
            guard let list = buckets[g], !list.isEmpty else { return nil }
            return (g, list)
        }
    }
}
'''.lstrip())

    w("Persistence/BookmarkRepository.swift", r'''
import Foundation
import SwiftData

@MainActor
final class BookmarkRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func all(sorted: Bool = true) throws -> [Bookmark] {
        var descriptor = FetchDescriptor<Bookmark>()
        if sorted {
            descriptor.sortBy = [
                SortDescriptor(\.isFavorite, order: .reverse),
                SortDescriptor(\.sortOrder),
                SortDescriptor(\.createdAt, order: .reverse)
            ]
        }
        return try modelContext.fetch(descriptor)
    }

    func favorites() throws -> [Bookmark] {
        let descriptor = FetchDescriptor<Bookmark>(
            predicate: #Predicate { $0.isFavorite == true },
            sortBy: [SortDescriptor(\.sortOrder)]
        )
        return try modelContext.fetch(descriptor)
    }

    func search(query: String) throws -> [Bookmark] {
        let all = try all()
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !q.isEmpty else { return all }
        return all.filter {
            $0.title.lowercased().contains(q) || $0.urlString.lowercased().contains(q)
        }
    }

    func folders() throws -> [BookmarkFolder] {
        let descriptor = FetchDescriptor<BookmarkFolder>(
            sortBy: [SortDescriptor(\.sortOrder)]
        )
        return try modelContext.fetch(descriptor)
    }

    @discardableResult
    func add(title: String, url: URL, isFavorite: Bool = false, folder: BookmarkFolder? = nil) throws -> Bookmark {
        let count = try all(sorted: false).count
        let bookmark = Bookmark(
            title: title.nilIfEmpty ?? url.dashsurfDomain,
            urlString: url.absoluteString,
            faviconURLString: FaviconService.guessURL(for: url)?.absoluteString,
            isFavorite: isFavorite,
            sortOrder: count,
            folder: folder
        )
        modelContext.insert(bookmark)
        try modelContext.save()
        return bookmark
    }

    func update(_ bookmark: Bookmark, title: String, url: URL, isFavorite: Bool) throws {
        bookmark.title = title
        bookmark.urlString = url.absoluteString
        bookmark.isFavorite = isFavorite
        bookmark.updatedAt = Date()
        try modelContext.save()
    }

    func delete(_ bookmark: Bookmark) throws {
        modelContext.delete(bookmark)
        try modelContext.save()
    }

    func toggleFavorite(_ bookmark: Bookmark) throws {
        bookmark.isFavorite.toggle()
        bookmark.updatedAt = Date()
        try modelContext.save()
    }

    @discardableResult
    func createFolder(named name: String) throws -> BookmarkFolder {
        let folder = BookmarkFolder(name: name, sortOrder: try folders().count)
        modelContext.insert(folder)
        try modelContext.save()
        return folder
    }

    func reorder(_ bookmarks: [Bookmark]) throws {
        for (index, bookmark) in bookmarks.enumerated() {
            bookmark.sortOrder = index
        }
        try modelContext.save()
    }
}
'''.lstrip())

    w("Persistence/RecentMediaRepository.swift", r'''
import Foundation
import SwiftData

@MainActor
final class RecentMediaRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func recent(limit: Int = 30) throws -> [RecentMediaItem] {
        var descriptor = FetchDescriptor<RecentMediaItem>(
            sortBy: [SortDescriptor(\.lastOpenedAt, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        return try modelContext.fetch(descriptor)
    }

    func favorites() throws -> [RecentMediaItem] {
        let descriptor = FetchDescriptor<RecentMediaItem>(
            predicate: #Predicate { $0.isFavorite == true },
            sortBy: [SortDescriptor(\.lastOpenedAt, order: .reverse)]
        )
        return try modelContext.fetch(descriptor)
    }

    func upsert(
        url: URL,
        title: String,
        provider: String,
        thumbnailURL: URL? = nil,
        playbackPosition: Double? = nil,
        duration: Double? = nil,
        lastKnownState: String? = nil
    ) throws {
        let urlString = url.absoluteString
        var descriptor = FetchDescriptor<RecentMediaItem>(
            predicate: #Predicate { $0.urlString == urlString }
        )
        descriptor.fetchLimit = 1
        if let existing = try modelContext.fetch(descriptor).first {
            existing.title = title
            existing.provider = provider
            existing.lastOpenedAt = Date()
            if let thumbnailURL { existing.thumbnailURLString = thumbnailURL.absoluteString }
            if let playbackPosition { existing.playbackPosition = playbackPosition }
            if let duration { existing.duration = duration }
            if let lastKnownState { existing.lastKnownState = lastKnownState }
        } else {
            let item = RecentMediaItem(
                urlString: urlString,
                title: title,
                provider: provider,
                thumbnailURLString: thumbnailURL?.absoluteString,
                playbackPosition: playbackPosition,
                duration: duration,
                lastKnownState: lastKnownState
            )
            modelContext.insert(item)
        }
        try modelContext.save()
    }

    func delete(_ item: RecentMediaItem) throws {
        modelContext.delete(item)
        try modelContext.save()
    }

    func toggleFavorite(_ item: RecentMediaItem) throws {
        item.isFavorite.toggle()
        try modelContext.save()
    }

    func clearAll() throws {
        try modelContext.delete(model: RecentMediaItem.self)
        try modelContext.save()
    }
}
'''.lstrip())

    w("Persistence/QuickAccessRepository.swift", r'''
import Foundation
import SwiftData

@MainActor
final class QuickAccessRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func all() throws -> [QuickAccessItem] {
        let descriptor = FetchDescriptor<QuickAccessItem>(
            sortBy: [
                SortDescriptor(\.isPinned, order: .reverse),
                SortDescriptor(\.sortOrder)
            ]
        )
        return try modelContext.fetch(descriptor)
    }

    func seedDefaultsIfNeeded() {
        do {
            if try all().isEmpty {
                for (index, item) in QuickAccessItem.defaults.enumerated() {
                    let row = QuickAccessItem(
                        title: item.0,
                        urlString: item.1,
                        symbolName: item.2,
                        sortOrder: index,
                        isPinned: index < 3
                    )
                    modelContext.insert(row)
                }
                try modelContext.save()
            }
        } catch {
            // Seed failure is non-fatal at launch.
        }
    }

    @discardableResult
    func add(title: String, url: URL, symbolName: String = "globe") throws -> QuickAccessItem {
        let item = QuickAccessItem(
            title: title,
            urlString: url.absoluteString,
            symbolName: symbolName,
            sortOrder: try all().count
        )
        modelContext.insert(item)
        try modelContext.save()
        return item
    }

    func update(_ item: QuickAccessItem, title: String, url: URL) throws {
        item.title = title
        item.urlString = url.absoluteString
        try modelContext.save()
    }

    func delete(_ item: QuickAccessItem) throws {
        modelContext.delete(item)
        try modelContext.save()
    }

    func reorder(_ items: [QuickAccessItem]) throws {
        for (index, item) in items.enumerated() {
            item.sortOrder = index
        }
        try modelContext.save()
    }

    func togglePin(_ item: QuickAccessItem) throws {
        item.isPinned.toggle()
        try modelContext.save()
    }
}
'''.lstrip())

    w("Persistence/TabStateRepository.swift", r'''
import Foundation
import SwiftData

@MainActor
final class TabStateRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func load() throws -> [BrowserTab] {
        let descriptor = FetchDescriptor<BrowserTabRecord>(
            sortBy: [SortDescriptor(\.sortOrder)]
        )
        return try modelContext.fetch(descriptor).map { record in
            BrowserTab(
                id: record.id,
                url: URL(string: record.urlString) ?? AppConstants.defaultHomepage,
                title: record.title,
                isActive: record.isActive,
                createdAt: record.createdAt,
                lastActiveAt: record.lastActiveAt,
                isPinned: record.isPinned
            )
        }
    }

    func save(_ tabs: [BrowserTab]) throws {
        try modelContext.delete(model: BrowserTabRecord.self)
        for (index, tab) in tabs.enumerated() {
            let record = BrowserTabRecord(
                id: tab.id,
                urlString: tab.url.absoluteString,
                title: tab.title,
                isActive: tab.isActive,
                createdAt: tab.createdAt,
                lastActiveAt: tab.lastActiveAt,
                isPinned: tab.isPinned,
                sortOrder: index
            )
            modelContext.insert(record)
        }
        try modelContext.save()
    }

    func clear() throws {
        try modelContext.delete(model: BrowserTabRecord.self)
        try modelContext.save()
    }
}
'''.lstrip())


def write_services() -> None:
    w("Services/URLService.swift", r'''
import Foundation

struct URLService {
    func resolve(_ input: String, searchEngine: SearchEngine) -> URL {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return AppConstants.defaultHomepage }

        if trimmed == "about:home" {
            return AppConstants.defaultHomepage
        }

        if let url = URL(string: trimmed), url.scheme != nil, url.host != nil {
            return url
        }

        if looksLikeDomain(trimmed) {
            let withScheme = trimmed.hasPrefix("//") ? "https:\(trimmed)" : "https://\(trimmed)"
            if let url = URL(string: withScheme) {
                return url
            }
        }

        return searchEngine.searchURL(for: trimmed)
    }

    private func looksLikeDomain(_ value: String) -> Bool {
        if value.contains(" ") { return false }
        if value.contains("/") { return true }
        return value.contains(".") && !value.hasPrefix(".")
    }

    static func normalizeForHistory(_ url: URL) -> URL {
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return url
        }
        components.fragment = nil
        // Drop common tracking params without rewriting meaningful paths.
        let drop: Set<String> = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"]
        if let items = components.queryItems {
            let filtered = items.filter { item in
                !drop.contains(item.name.lowercased())
            }
            components.queryItems = filtered.isEmpty ? nil : filtered
        }
        return components.url ?? url
    }
}
'''.lstrip())

    w("Services/SearchService.swift", r'''
import Foundation

struct SearchService {
    func makeSearchURL(query: String, engine: SearchEngine) -> URL {
        engine.searchURL(for: query)
    }
}
'''.lstrip())

    w("Services/FaviconService.swift", r'''
import Foundation

actor FaviconService {
    static func guessURL(for pageURL: URL) -> URL? {
        guard let host = pageURL.host else { return nil }
        return URL(string: "https://www.google.com/s2/favicons?domain=\(host)&sz=64")
    }

    func favicon(for pageURL: URL) async -> URL? {
        Self.guessURL(for: pageURL)
    }
}
'''.lstrip())

    w("Services/MediaDetectionService.swift", r'''
import Foundation

struct DetectedMedia: Equatable {
    var url: URL
    var title: String
    var provider: String
    var thumbnailURL: URL?
}

struct MediaDetectionService {
    func detect(url: URL, pageTitle: String?) -> DetectedMedia? {
        let host = url.host?.lowercased() ?? ""
        let path = url.path.lowercased()

        if host.contains("youtube.com") || host == "youtu.be" {
            if path.contains("/watch") || host == "youtu.be" || path.contains("/shorts/") {
                let id = youtubeID(from: url)
                let thumb = id.flatMap { URL(string: "https://i.ytimg.com/vi/\($0)/hqdefault.jpg") }
                return DetectedMedia(
                    url: url,
                    title: pageTitle?.nilIfEmpty ?? "YouTube",
                    provider: "YouTube",
                    thumbnailURL: thumb
                )
            }
            return nil
        }

        if host.contains("twitch.tv") {
            if path.split(separator: "/").count >= 1 && !path.contains("/directory") {
                return DetectedMedia(
                    url: url,
                    title: pageTitle?.nilIfEmpty ?? "Twitch",
                    provider: "Twitch",
                    thumbnailURL: nil
                )
            }
            return nil
        }

        if host.contains("vimeo.com") {
            return DetectedMedia(
                url: url,
                title: pageTitle?.nilIfEmpty ?? "Vimeo",
                provider: "Vimeo",
                thumbnailURL: nil
            )
        }

        if host.contains("netflix.com") && (path.contains("/watch") || path.contains("/title")) {
            // DRM may block WKWebView playback; we still remember the page for Continue Watching.
            return DetectedMedia(
                url: url,
                title: pageTitle?.nilIfEmpty ?? "Netflix",
                provider: "Netflix",
                thumbnailURL: nil
            )
        }

        return nil
    }

    private func youtubeID(from url: URL) -> String? {
        if url.host?.contains("youtu.be") == true {
            return url.pathComponents.dropFirst().first
        }
        if let comps = URLComponents(url: url, resolvingAgainstBaseURL: false),
           let v = comps.queryItems?.first(where: { $0.name == "v" })?.value {
            return v
        }
        let parts = url.path.split(separator: "/")
        if let shortsIndex = parts.firstIndex(of: "shorts"), parts.indices.contains(shortsIndex + 1) {
            return String(parts[shortsIndex + 1])
        }
        return nil
    }
}
'''.lstrip())

    w("Services/WebsiteDataService.swift", r'''
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
'''.lstrip())

    w("Services/AudioSessionService.swift", r'''
import AVFoundation

actor AudioSessionService {
    static let shared = AudioSessionService()

    func activatePlaybackCategory() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .moviePlayback, options: [.allowAirPlay, .allowBluetoothA2DP])
            try session.setActive(true)
        } catch {
            // Ignore — sites can still play with system defaults.
        }
    }
}
'''.lstrip())

    w("Services/SettingsStore.swift", r'''
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
'''.lstrip())


print("persistence+services functions defined")
