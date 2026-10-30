import Foundation
import SwiftData

@MainActor
final class PersistenceController {
    let container: ModelContainer

    init(inMemory: Bool = false) {
        let schema = Schema([
            BrowserHistoryItem.self,
            Bookmark.self,
            BookmarkFolder.self,
            RecentMediaItem.self,
            QuickAccessItem.self,
            BrowserTabRecord.self
        ])
        let config = ModelConfiguration(
            "DashSurf",
            schema: schema,
            isStoredInMemoryOnly: inMemory
        )
        do {
            container = try ModelContainer(for: schema, configurations: [config])
        } catch {
            fatalError("DashSurf failed to create ModelContainer: \(error)")
        }
    }

    static func makeShared() -> PersistenceController {
        PersistenceController(inMemory: false)
    }

    static func makePreview() -> PersistenceController {
        PersistenceController(inMemory: true)
    }
}
