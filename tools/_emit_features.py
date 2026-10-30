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


def write_features() -> None:
    w("Features/Home/HomeView.swift", r'''
import SwiftUI
import SwiftData

struct HomeView: View {
    @ObservedObject var coordinator: AppCoordinator
    @EnvironmentObject private var dependencies: AppDependencies
    @EnvironmentObject private var session: BrowserSessionManager
    @Query(sort: \QuickAccessItem.sortOrder) private var quickAccess: [QuickAccessItem]
    @Query(sort: \RecentMediaItem.lastOpenedAt, order: .reverse) private var recentMedia: [RecentMediaItem]
    @Query(sort: \BrowserHistoryItem.lastVisitedAt, order: .reverse) private var history: [BrowserHistoryItem]
    @Query(filter: #Predicate<Bookmark> { $0.isFavorite == true }, sort: \Bookmark.sortOrder)
    private var favorites: [Bookmark]

    @State private var searchText = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    header
                    searchField
                    QuickAccessSection(items: quickAccess) { item in
                        open(item.url)
                    }
                    if !recentMedia.isEmpty {
                        ContinueWatchingSection(items: Array(recentMedia.prefix(12))) { item in
                            open(item.url)
                        }
                    }
                    if !history.isEmpty {
                        RecentlyVisitedSection(items: Array(history.prefix(8))) { item in
                            open(item.url)
                        }
                    }
                    if !favorites.isEmpty {
                        FavoritesSection(items: favorites) { bookmark in
                            open(bookmark.url)
                        }
                    }
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 32)
            }
            .background(DashSurfTheme.backgroundGradient.ignoresSafeArea())
            .navigationBarHidden(true)
        }
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("DashSurf")
                    .font(.largeTitle.weight(.bold))
                    .foregroundStyle(DashSurfTheme.primaryText)
                Text(AppConstants.slogan)
                    .font(.subheadline)
                    .foregroundStyle(DashSurfTheme.secondaryText)
            }
            Spacer()
            Button {
                coordinator.selectedTab = .settings
            } label: {
                Image(systemName: "gearshape.fill")
                    .font(.title3)
                    .foregroundStyle(DashSurfTheme.secondaryText)
                    .frame(width: 40, height: 40)
                    .background(DashSurfTheme.secondaryBackground, in: Circle())
            }
        }
        .padding(.top, 12)
    }

    private var searchField: some View {
        HStack {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(DashSurfTheme.secondaryText)
            TextField("Search or enter website", text: $searchText)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .submitLabel(.go)
                .onSubmit {
                    let url = dependencies.urlService.resolve(searchText, searchEngine: dependencies.settingsStore.searchEngine)
                    open(url)
                    searchText = ""
                }
        }
        .padding(16)
        .background(DashSurfTheme.secondaryBackground, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private func open(_ url: URL?) {
        guard let url else { return }
        coordinator.openInBrowser(url)
    }
}

struct QuickAccessSection: View {
    let items: [QuickAccessItem]
    var onOpen: (QuickAccessItem) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Quick Access")
                .font(.headline)
                .foregroundStyle(DashSurfTheme.primaryText)
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 12), count: 4), spacing: 16) {
                ForEach(items) { item in
                    Button { onOpen(item) } label: {
                        VStack(spacing: 8) {
                            Image(systemName: item.symbolName)
                                .font(.title2)
                                .frame(width: 56, height: 56)
                                .background(DashSurfTheme.secondaryBackground, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                                .foregroundStyle(DashSurfTheme.accent)
                            Text(item.title)
                                .font(.caption)
                                .foregroundStyle(DashSurfTheme.secondaryText)
                                .lineLimit(1)
                        }
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}

struct ContinueWatchingSection: View {
    let items: [RecentMediaItem]
    var onOpen: (RecentMediaItem) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Continue Watching")
                .font(.headline)
                .foregroundStyle(DashSurfTheme.primaryText)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 14) {
                    ForEach(items) { item in
                        Button { onOpen(item) } label: {
                            VStack(alignment: .leading, spacing: 8) {
                                ZStack {
                                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                                        .fill(DashSurfTheme.secondaryBackground)
                                        .frame(width: 160, height: 90)
                                    if let thumb = item.thumbnailURL {
                                        AsyncImage(url: thumb) { phase in
                                            switch phase {
                                            case .success(let image):
                                                image.resizable().scaledToFill()
                                            default:
                                                Image(systemName: "play.rectangle.fill")
                                                    .foregroundStyle(DashSurfTheme.accent)
                                            }
                                        }
                                        .frame(width: 160, height: 90)
                                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                                    } else {
                                        Image(systemName: "play.rectangle.fill")
                                            .foregroundStyle(DashSurfTheme.accent)
                                    }
                                }
                                Text(item.title)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(DashSurfTheme.primaryText)
                                    .lineLimit(2)
                                    .frame(width: 160, alignment: .leading)
                                Text(item.provider)
                                    .font(.caption2)
                                    .foregroundStyle(DashSurfTheme.secondaryText)
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }
}

struct RecentlyVisitedSection: View {
    let items: [BrowserHistoryItem]
    var onOpen: (BrowserHistoryItem) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recently Visited")
                .font(.headline)
                .foregroundStyle(DashSurfTheme.primaryText)
            VStack(spacing: 0) {
                ForEach(items) { item in
                    Button { onOpen(item) } label: {
                        HStack(spacing: 12) {
                            Image(systemName: "globe")
                                .foregroundStyle(DashSurfTheme.accent)
                                .frame(width: 28)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(item.title)
                                    .foregroundStyle(DashSurfTheme.primaryText)
                                    .lineLimit(1)
                                Text(item.domain)
                                    .font(.caption)
                                    .foregroundStyle(DashSurfTheme.secondaryText)
                            }
                            Spacer()
                        }
                        .padding(.vertical, 10)
                    }
                    .buttonStyle(.plain)
                    if item.id != items.last?.id {
                        Divider().overlay(DashSurfTheme.secondaryBackground)
                    }
                }
            }
        }
    }
}

struct FavoritesSection: View {
    let items: [Bookmark]
    var onOpen: (Bookmark) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Favorites")
                .font(.headline)
                .foregroundStyle(DashSurfTheme.primaryText)
            ForEach(items) { bookmark in
                Button { onOpen(bookmark) } label: {
                    HStack {
                        Image(systemName: "star.fill")
                            .foregroundStyle(DashSurfTheme.accent)
                        Text(bookmark.title)
                            .foregroundStyle(DashSurfTheme.primaryText)
                        Spacer()
                    }
                    .padding(.vertical, 8)
                }
                .buttonStyle(.plain)
            }
        }
    }
}
'''.lstrip())

    w("Features/History/HistoryView.swift", r'''
import SwiftUI

struct HistoryView: View {
    @ObservedObject var coordinator: AppCoordinator
    @EnvironmentObject private var dependencies: AppDependencies
    @State private var query = ""
    @State private var groups: [(HistoryDateGroup, [BrowserHistoryItem])] = []
    @State private var showClearConfirm = false

    var body: some View {
        NavigationStack {
            List {
                ForEach(groups, id: \.0) { group, items in
                    Section(group.rawValue) {
                        ForEach(items) { item in
                            Button {
                                coordinator.openInBrowser(item.url ?? AppConstants.defaultHomepage)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(item.title).foregroundStyle(DashSurfTheme.primaryText)
                                    Text(item.urlString)
                                        .font(.caption)
                                        .foregroundStyle(DashSurfTheme.secondaryText)
                                        .lineLimit(1)
                                }
                            }
                            .swipeActions {
                                Button(role: .destructive) {
                                    try? dependencies.historyRepository.delete(item)
                                    reload()
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
            .searchable(text: $query, prompt: "Search history")
            .onChange(of: query) { _, _ in reload() }
            .navigationTitle("History")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Clear", role: .destructive) { showClearConfirm = true }
                }
            }
            .alert("Clear all history?", isPresented: $showClearConfirm) {
                Button("Clear", role: .destructive) {
                    try? dependencies.historyRepository.clearAll()
                    reload()
                }
                Button("Cancel", role: .cancel) {}
            }
            .onAppear(perform: reload)
        }
    }

    private func reload() {
        groups = (try? dependencies.historyRepository.grouped(query: query)) ?? []
    }
}
'''.lstrip())

    w("Features/Bookmarks/BookmarksView.swift", r'''
import SwiftUI

struct BookmarksView: View {
    @ObservedObject var coordinator: AppCoordinator
    @EnvironmentObject private var dependencies: AppDependencies
    @State private var bookmarks: [Bookmark] = []
    @State private var query = ""
    @State private var showAdd = false
    @State private var draftTitle = ""
    @State private var draftURL = ""

    var body: some View {
        NavigationStack {
            List {
                ForEach(bookmarks) { bookmark in
                    Button {
                        coordinator.openInBrowser(bookmark.url ?? AppConstants.defaultHomepage)
                    } label: {
                        HStack {
                            Image(systemName: bookmark.isFavorite ? "star.fill" : "bookmark.fill")
                                .foregroundStyle(DashSurfTheme.accent)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(bookmark.title).foregroundStyle(DashSurfTheme.primaryText)
                                Text(bookmark.urlString)
                                    .font(.caption)
                                    .foregroundStyle(DashSurfTheme.secondaryText)
                                    .lineLimit(1)
                            }
                        }
                    }
                    .swipeActions(edge: .trailing) {
                        Button(role: .destructive) {
                            try? dependencies.bookmarkRepository.delete(bookmark)
                            reload()
                        } label: { Label("Delete", systemImage: "trash") }
                    }
                    .swipeActions(edge: .leading) {
                        Button {
                            try? dependencies.bookmarkRepository.toggleFavorite(bookmark)
                            reload()
                        } label: { Label("Favorite", systemImage: "star") }
                        .tint(DashSurfTheme.accent)
                    }
                }
                .onMove(perform: move)
            }
            .scrollContentBackground(.hidden)
            .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
            .searchable(text: $query)
            .onChange(of: query) { _, _ in reload() }
            .navigationTitle("Bookmarks")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showAdd = true } label: { Image(systemName: "plus") }
                }
                ToolbarItem(placement: .topBarLeading) { EditButton() }
            }
            .sheet(isPresented: $showAdd) {
                NavigationStack {
                    Form {
                        TextField("Title", text: $draftTitle)
                        TextField("URL", text: $draftURL)
                            .textInputAutocapitalization(.never)
                            .keyboardType(.URL)
                    }
                    .navigationTitle("Add Bookmark")
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) { Button("Cancel") { showAdd = false } }
                        ToolbarItem(placement: .confirmationAction) {
                            Button("Save") {
                                if let url = URL(string: draftURL) {
                                    _ = try? dependencies.bookmarkRepository.add(title: draftTitle, url: url)
                                    reload()
                                }
                                showAdd = false
                                draftTitle = ""
                                draftURL = ""
                            }
                        }
                    }
                }
            }
            .onAppear(perform: reload)
        }
    }

    private func reload() {
        bookmarks = (try? dependencies.bookmarkRepository.search(query: query)) ?? []
    }

    private func move(from source: IndexSet, to destination: Int) {
        bookmarks.move(fromOffsets: source, toOffset: destination)
        try? dependencies.bookmarkRepository.reorder(bookmarks)
    }
}
'''.lstrip())

    w("Features/RecentMedia/RecentMediaView.swift", r'''
import SwiftUI

struct RecentMediaView: View {
    @EnvironmentObject private var dependencies: AppDependencies
    @State private var items: [RecentMediaItem] = []

    var body: some View {
        List {
            ForEach(items) { item in
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.title)
                    Text("\(item.provider) · \(item.urlString)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
        }
        .onAppear {
            items = (try? dependencies.recentMediaRepository.recent()) ?? []
        }
    }
}
'''.lstrip())

    w("Features/QuickAccess/QuickAccessEditorView.swift", r'''
import SwiftUI

struct QuickAccessEditorView: View {
    @EnvironmentObject private var dependencies: AppDependencies
    @State private var items: [QuickAccessItem] = []
    @State private var showAdd = false
    @State private var title = ""
    @State private var urlString = ""

    var body: some View {
        List {
            ForEach(items) { item in
                HStack {
                    Image(systemName: item.symbolName)
                    VStack(alignment: .leading) {
                        Text(item.title)
                        Text(item.urlString).font(.caption).foregroundStyle(.secondary)
                    }
                }
                .swipeActions {
                    Button(role: .destructive) {
                        try? dependencies.quickAccessRepository.delete(item)
                        reload()
                    } label: { Label("Delete", systemImage: "trash") }
                    Button {
                        try? dependencies.quickAccessRepository.togglePin(item)
                        reload()
                    } label: { Label("Pin", systemImage: "pin") }
                }
            }
            .onMove { source, dest in
                items.move(fromOffsets: source, toOffset: dest)
                try? dependencies.quickAccessRepository.reorder(items)
            }
        }
        .navigationTitle("Quick Access")
        .toolbar {
            EditButton()
            Button { showAdd = true } label: { Image(systemName: "plus") }
        }
        .sheet(isPresented: $showAdd) {
            Form {
                TextField("Name", text: $title)
                TextField("URL", text: $urlString)
                Button("Add") {
                    if let url = URL(string: urlString) {
                        _ = try? dependencies.quickAccessRepository.add(title: title, url: url)
                        reload()
                    }
                    showAdd = false
                }
            }
        }
        .onAppear(perform: reload)
    }

    private func reload() {
        items = (try? dependencies.quickAccessRepository.all()) ?? []
    }
}
'''.lstrip())

    w("Features/Settings/SettingsView.swift", r'''
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: SettingsStore
    @EnvironmentObject private var dependencies: AppDependencies
    @EnvironmentObject private var carPlay: CarPlayAvailabilityService
    @State private var confirmClearHistory = false
    @State private var confirmClearCookies = false
    @State private var confirmClearMedia = false
    @State private var statusMessage: String?

    var body: some View {
        NavigationStack {
            List {
                Section("General") {
                    Picker("Appearance", selection: $settings.colorSchemePreference) {
                        ForEach(AppearancePreference.allCases) { pref in
                            Text(pref.title).tag(pref)
                        }
                    }
                    Picker("Default Search Engine", selection: $settings.searchEngine) {
                        ForEach(SearchEngine.allCases) { engine in
                            Text(engine.title).tag(engine)
                        }
                    }
                    TextField("Homepage", text: $settings.homepageURLString)
                        .textInputAutocapitalization(.never)
                    Toggle("Restore Tabs on Launch", isOn: $settings.restoreTabsOnLaunch)
                    Toggle("Desktop Mode Default", isOn: $settings.desktopModeDefault)
                }

                Section("Privacy") {
                    Toggle("Enable History Recording", isOn: $settings.historyRecordingEnabled)
                    Button("Clear History", role: .destructive) { confirmClearHistory = true }
                    Button("Clear Cookies & Website Data", role: .destructive) { confirmClearCookies = true }
                    Button("Clear Recent Media", role: .destructive) { confirmClearMedia = true }
                    NavigationLink("Edit Quick Access") {
                        QuickAccessEditorView()
                    }
                }

                Section("CarPlay") {
                    LabeledContent("Connection") {
                        Text(carPlay.connectionLabel)
                            .foregroundStyle(DashSurfTheme.secondaryText)
                    }
                    LabeledContent("Availability") {
                        Text(carPlay.status.summary)
                            .foregroundStyle(DashSurfTheme.secondaryText)
                            .multilineTextAlignment(.trailing)
                    }
                    ForEach(carPlay.capabilityNotes, id: \.self) { note in
                        Text(note)
                            .font(.footnote)
                            .foregroundStyle(DashSurfTheme.secondaryText)
                    }
                    NavigationLink("Compatibility Details") {
                        CarPlayCompatibilityInfoView()
                    }
                }

                Section("About") {
                    LabeledContent("DashSurf", value: AppConstants.slogan)
                    LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0")
                    NavigationLink("Licenses") { LicensesView() }
                    NavigationLink("Privacy Information") { PrivacyInfoView() }
                }

                if let statusMessage {
                    Section {
                        Text(statusMessage).foregroundStyle(DashSurfTheme.accent)
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
            .navigationTitle("Settings")
            .alert("Clear browsing history?", isPresented: $confirmClearHistory) {
                Button("Clear", role: .destructive) {
                    try? dependencies.historyRepository.clearAll()
                    statusMessage = "History cleared."
                }
                Button("Cancel", role: .cancel) {}
            }
            .alert("Clear cookies and website data?", isPresented: $confirmClearCookies) {
                Button("Clear", role: .destructive) {
                    Task {
                        await dependencies.websiteDataService.clearAllWebsiteData()
                        statusMessage = "Website data cleared. You will be signed out of sites."
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This signs you out of websites inside DashSurf. Safari is not affected.")
            }
            .alert("Clear Continue Watching?", isPresented: $confirmClearMedia) {
                Button("Clear", role: .destructive) {
                    try? dependencies.recentMediaRepository.clearAll()
                    statusMessage = "Recent media cleared."
                }
                Button("Cancel", role: .cancel) {}
            }
        }
    }
}

struct CarPlayCompatibilityInfoView: View {
    var body: some View {
        ScrollView {
            Text(CarPlayCompatibilityCopy.summary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
        }
        .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
        .navigationTitle("CarPlay")
    }
}

struct LicensesView: View {
    var body: some View {
        ScrollView {
            Text(
                """
                DashSurf is original software.

                Architectural reference (MIT): Cafari Lite by rPlayAI — concepts for UIWindowSceneSessionRoleCarPlay scene wiring. No source was copied verbatim beyond publicly documented scene role strings and entitlement key names.

                APTV (Kimentanm/aptv) was used only as a product inspiration. Its repository has no open-source license for app code reuse; nothing from APTV was copied.

                Apple frameworks (WebKit, SwiftUI, SwiftData, CarPlay, AVFoundation) remain Apple property and are used via public APIs only.
                """
            )
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
        .navigationTitle("Licenses")
    }
}

struct PrivacyInfoView: View {
    var body: some View {
        ScrollView {
            Text(
                """
                DashSurf stores browsing history, bookmarks, tabs, quick access shortcuts and Continue Watching metadata locally on your device using SwiftData.

                Website cookies and localStorage are stored by WebKit through WKWebsiteDataStore.default(). DashSurf does not operate an account server and does not upload your history.

                Passwords are never captured by DashSurf. Use the site’s own login forms. Google and other providers may block embedded WebView sign-in; use Open in Safari when prompted.

                Location permission (optional) is only used to estimate whether the car is moving so car-screen video can be paused while driving. Coordinates are not stored or transmitted.
                """
            )
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
        .navigationTitle("Privacy")
    }
}

enum CarPlayCompatibilityCopy {
    static let summary = """
    DashSurf’s phone browser does not require CarPlay entitlements.

    Optional car window support uses UIWindowSceneSessionRoleCarPlay (documented scene role string). Apple must grant com.apple.developer.carplay-video and typically also com.apple.developer.carplay-audio before iOS will create that scene.

    Request entitlements at https://developer.apple.com/contact/carplay/ then sign with CarPlay.entitlements.

    Official CarPlay Video apps (CarPlay framework templates + AirPlay) are a separate, App Review–oriented path. Arbitrary unrestricted browsing on the head unit is not guaranteed by Apple and may change across iOS releases.

    See CARPLAY_COMPATIBILITY.md in the repository for full details.
    """
}
'''.lstrip())


print("features ok")
