import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var dependencies: AppDependencies
    @EnvironmentObject private var session: BrowserSessionManager
    @EnvironmentObject private var settings: SettingsStore
    @StateObject private var nav = AppCoordinator()

    var body: some View {
        TabView(selection: $nav.selectedTab) {
            HomeView(coordinator: nav)
                .tabItem { Label("Home", systemImage: "house.fill") }
                .tag(AppCoordinator.Destination.home)

            BrowserContainerView(coordinator: nav)
                .tabItem { Label("Browser", systemImage: "safari.fill") }
                .tag(AppCoordinator.Destination.browser)

            HistoryView(coordinator: nav)
                .tabItem { Label("History", systemImage: "clock.fill") }
                .tag(AppCoordinator.Destination.history)

            BookmarksView(coordinator: nav)
                .tabItem { Label("Bookmarks", systemImage: "bookmark.fill") }
                .tag(AppCoordinator.Destination.bookmarks)

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape.fill") }
                .tag(AppCoordinator.Destination.settings)
        }
        .tint(DashSurfTheme.accent)
        .onChange(of: nav.pendingURLToOpen) { _, url in
            guard let url else { return }
            session.openURL(url, inNewTab: false)
            nav.clearPendingURL()
        }
        .environmentObject(nav)
    }
}
