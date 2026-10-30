import Foundation
import SwiftData

@Model
final class BrowserHistoryItem {
    @Attribute(.unique) var id: UUID
    var urlString: String
    var title: String
    var domain: String
    var faviconURLString: String?
    var firstVisitedAt: Date
    var lastVisitedAt: Date
    var visitCount: Int

    init(
        id: UUID = UUID(),
        urlString: String,
        title: String,
        domain: String,
        faviconURLString: String? = nil,
        firstVisitedAt: Date = Date(),
        lastVisitedAt: Date = Date(),
        visitCount: Int = 1
    ) {
        self.id = id
        self.urlString = urlString
        self.title = title
        self.domain = domain
        self.faviconURLString = faviconURLString
        self.firstVisitedAt = firstVisitedAt
        self.lastVisitedAt = lastVisitedAt
        self.visitCount = visitCount
    }

    var url: URL? { URL(string: urlString) }
}
