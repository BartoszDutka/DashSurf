import Foundation
import SwiftData

@Model
final class BrowserTabRecord {
    @Attribute(.unique) var id: UUID
    var urlString: String
    var title: String
    var isActive: Bool
    var createdAt: Date
    var lastActiveAt: Date
    var isPinned: Bool
    var sortOrder: Int

    init(
        id: UUID = UUID(),
        urlString: String = "about:home",
        title: String = "New Tab",
        isActive: Bool = false,
        createdAt: Date = Date(),
        lastActiveAt: Date = Date(),
        isPinned: Bool = false,
        sortOrder: Int = 0
    ) {
        self.id = id
        self.urlString = urlString
        self.title = title
        self.isActive = isActive
        self.createdAt = createdAt
        self.lastActiveAt = lastActiveAt
        self.isPinned = isPinned
        self.sortOrder = sortOrder
    }
}

struct BrowserTab: Identifiable, Equatable, Hashable {
    var id: UUID
    var url: URL
    var title: String
    var isActive: Bool
    var createdAt: Date
    var lastActiveAt: Date
    var isPinned: Bool

    static func fresh(isActive: Bool = true) -> BrowserTab {
        let now = Date()
        return BrowserTab(
            id: UUID(),
            url: AppConstants.defaultHomepage,
            title: "New Tab",
            isActive: isActive,
            createdAt: now,
            lastActiveAt: now,
            isPinned: false
        )
    }
}
