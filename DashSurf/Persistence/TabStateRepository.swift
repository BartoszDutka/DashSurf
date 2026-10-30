import Foundation
import SwiftData

@MainActor
final class TabStateRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func load() throws -> [BrowserTab] {
        let descriptor = FetchDescriptor<BrowserTabRecord>(
            sortBy: [SortDescriptor(\BrowserTabRecord.sortOrder)]
        )
        return try modelContext.fetch(descriptor).map { record in
            BrowserTab(
                id: record.id,
                url: URL(string: record.urlString) ?? AppConstants.defaultHomepage,
                title: record.title,
                isActive: record.isActive,
                createdAt: record.createdAt,
                lastActiveAt: record.lastActiveAt,
                isPinned: record.isPinned
            )
        }
    }

    func save(_ tabs: [BrowserTab]) throws {
        try modelContext.delete(model: BrowserTabRecord.self)
        for (index, tab) in tabs.enumerated() {
            let record = BrowserTabRecord(
                id: tab.id,
                urlString: tab.url.absoluteString,
                title: tab.title,
                isActive: tab.isActive,
                createdAt: tab.createdAt,
                lastActiveAt: tab.lastActiveAt,
                isPinned: tab.isPinned,
                sortOrder: index
            )
            modelContext.insert(record)
        }
        try modelContext.save()
    }

    func clear() throws {
        try modelContext.delete(model: BrowserTabRecord.self)
        try modelContext.save()
    }
}
