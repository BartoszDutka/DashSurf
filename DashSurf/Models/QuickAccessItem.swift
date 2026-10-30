import Foundation
import SwiftData

@Model
final class QuickAccessItem {
    @Attribute(.unique) var id: UUID
    var title: String
    var urlString: String
    var symbolName: String
    var sortOrder: Int
    var isPinned: Bool
    var createdAt: Date

    init(
        id: UUID = UUID(),
        title: String,
        urlString: String,
        symbolName: String,
        sortOrder: Int,
        isPinned: Bool = false,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.title = title
        self.urlString = urlString
        self.symbolName = symbolName
        self.sortOrder = sortOrder
        self.isPinned = isPinned
        self.createdAt = createdAt
    }

    var url: URL? { URL(string: urlString) }

    static let defaults: [(String, String, String)] = [
        ("YouTube", "https://m.youtube.com", "play.rectangle.fill"),
        ("Netflix", "https://www.netflix.com", "film"),
        ("Twitch", "https://m.twitch.tv", "dot.radiowaves.left.and.right"),
        ("Google", "https://www.google.com", "magnifyingglass"),
        ("Reddit", "https://www.reddit.com", "bubble.left.and.bubble.right.fill")
    ]
}
