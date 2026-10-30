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
