import XCTest
import SwiftData
@testable import DashSurf

@MainActor
final class RecentMediaRepositoryTests: XCTestCase {
    func testUpsertRecentMedia() throws {
        let persistence = PersistenceController(inMemory: true)
        let repo = RecentMediaRepository(modelContext: ModelContext(persistence.container))
        let url = URL(string: "https://www.youtube.com/watch?v=dQw4w9WgXcQ")!
        try repo.upsert(url: url, title: "Video", provider: "YouTube")
        try repo.upsert(url: url, title: "Video Updated", provider: "YouTube")
        let items = try repo.recent()
        XCTAssertEqual(items.count, 1)
        XCTAssertEqual(items.first?.title, "Video Updated")
    }
}
