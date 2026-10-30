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
