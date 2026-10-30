import Foundation
import SwiftData

@MainActor
final class RecentMediaRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func recent(limit: Int = 30) throws -> [RecentMediaItem] {
        var descriptor = FetchDescriptor<RecentMediaItem>(
            sortBy: [SortDescriptor(\.lastOpenedAt, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        return try modelContext.fetch(descriptor)
    }

    func favorites() throws -> [RecentMediaItem] {
        let descriptor = FetchDescriptor<RecentMediaItem>(
            predicate: #Predicate { $0.isFavorite == true },
            sortBy: [SortDescriptor(\.lastOpenedAt, order: .reverse)]
        )
        return try modelContext.fetch(descriptor)
    }

    func upsert(
        url: URL,
        title: String,
        provider: String,
        thumbnailURL: URL? = nil,
        playbackPosition: Double? = nil,
        duration: Double? = nil,
        lastKnownState: String? = nil
    ) throws {
        let urlString = url.absoluteString
        var descriptor = FetchDescriptor<RecentMediaItem>(
            predicate: #Predicate { $0.urlString == urlString }
        )
        descriptor.fetchLimit = 1
        if let existing = try modelContext.fetch(descriptor).first {
            existing.title = title
            existing.provider = provider
            existing.lastOpenedAt = Date()
            if let thumbnailURL { existing.thumbnailURLString = thumbnailURL.absoluteString }
            if let playbackPosition { existing.playbackPosition = playbackPosition }
            if let duration { existing.duration = duration }
            if let lastKnownState { existing.lastKnownState = lastKnownState }
        } else {
            let item = RecentMediaItem(
                urlString: urlString,
                title: title,
                provider: provider,
                thumbnailURLString: thumbnailURL?.absoluteString,
                playbackPosition: playbackPosition,
                duration: duration,
                lastKnownState: lastKnownState
            )
            modelContext.insert(item)
        }
        try modelContext.save()
    }

    func delete(_ item: RecentMediaItem) throws {
        modelContext.delete(item)
        try modelContext.save()
    }

    func toggleFavorite(_ item: RecentMediaItem) throws {
        item.isFavorite.toggle()
        try modelContext.save()
    }

    func clearAll() throws {
        try modelContext.delete(model: RecentMediaItem.self)
        try modelContext.save()
    }
}
