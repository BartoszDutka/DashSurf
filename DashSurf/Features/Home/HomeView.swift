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
