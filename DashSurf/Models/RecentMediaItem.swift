import Foundation
import SwiftData

@Model
final class RecentMediaItem {
    @Attribute(.unique) var id: UUID
    var urlString: String
    var title: String
    var provider: String
    var thumbnailURLString: String?
    var lastOpenedAt: Date
    var playbackPosition: Double?
    var duration: Double?
    var lastKnownState: String?
    var isFavorite: Bool

    init(
        id: UUID = UUID(),
        urlString: String,
        title: String,
        provider: String,
        thumbnailURLString: String? = nil,
        lastOpenedAt: Date = Date(),
        playbackPosition: Double? = nil,
        duration: Double? = nil,
        lastKnownState: String? = nil,
        isFavorite: Bool = false
    ) {
        self.id = id
        self.urlString = urlString
        self.title = title
        self.provider = provider
        self.thumbnailURLString = thumbnailURLString
        self.lastOpenedAt = lastOpenedAt
        self.playbackPosition = playbackPosition
        self.duration = duration
        self.lastKnownState = lastKnownState
        self.isFavorite = isFavorite
    }

    var url: URL? { URL(string: urlString) }
    var thumbnailURL: URL? { thumbnailURLString.flatMap(URL.init(string:)) }
}
