import Foundation
import SwiftData

@MainActor
final class QuickAccessRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func all() throws -> [QuickAccessItem] {
        let descriptor = FetchDescriptor<QuickAccessItem>(
            sortBy: [
                SortDescriptor(\.isPinned, order: .reverse),
                SortDescriptor(\.sortOrder)
            ]
        )
        return try modelContext.fetch(descriptor)
    }

    func seedDefaultsIfNeeded() {
        do {
            if try all().isEmpty {
                for (index, item) in QuickAccessItem.defaults.enumerated() {
                    let row = QuickAccessItem(
                        title: item.0,
                        urlString: item.1,
                        symbolName: item.2,
                        sortOrder: index,
                        isPinned: index < 3
                    )
                    modelContext.insert(row)
                }
                try modelContext.save()
            }
        } catch {
            // Seed failure is non-fatal at launch.
        }
    }

    @discardableResult
    func add(title: String, url: URL, symbolName: String = "globe") throws -> QuickAccessItem {
        let item = QuickAccessItem(
            title: title,
            urlString: url.absoluteString,
            symbolName: symbolName,
            sortOrder: try all().count
        )
        modelContext.insert(item)
        try modelContext.save()
        return item
    }

    func update(_ item: QuickAccessItem, title: String, url: URL) throws {
        item.title = title
        item.urlString = url.absoluteString
        try modelContext.save()
    }

    func delete(_ item: QuickAccessItem) throws {
        modelContext.delete(item)
        try modelContext.save()
    }

    func reorder(_ items: [QuickAccessItem]) throws {
        for (index, item) in items.enumerated() {
            item.sortOrder = index
        }
        try modelContext.save()
    }

    func togglePin(_ item: QuickAccessItem) throws {
        item.isPinned.toggle()
        try modelContext.save()
    }
}
