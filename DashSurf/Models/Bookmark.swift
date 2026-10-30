import Foundation
import SwiftData

@Model
final class BookmarkFolder {
    @Attribute(.unique) var id: UUID
    var name: String
    var createdAt: Date
    var sortOrder: Int
    @Relationship(deleteRule: .cascade, inverse: \Bookmark.folder)
    var bookmarks: [Bookmark]

    init(id: UUID = UUID(), name: String, createdAt: Date = Date(), sortOrder: Int = 0) {
        self.id = id
        self.name = name
        self.createdAt = createdAt
        self.sortOrder = sortOrder
        self.bookmarks = []
    }
}

@Model
final class Bookmark {
    @Attribute(.unique) var id: UUID
    var title: String
    var urlString: String
    var faviconURLString: String?
    var isFavorite: Bool
    var createdAt: Date
    var updatedAt: Date
    var sortOrder: Int
    var folder: BookmarkFolder?

    init(
        id: UUID = UUID(),
        title: String,
        urlString: String,
        faviconURLString: String? = nil,
        isFavorite: Bool = false,
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        sortOrder: Int = 0,
        folder: BookmarkFolder? = nil
    ) {
        self.id = id
        self.title = title
        self.urlString = urlString
        self.faviconURLString = faviconURLString
        self.isFavorite = isFavorite
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.sortOrder = sortOrder
        self.folder = folder
    }

    var url: URL? { URL(string: urlString) }
}
