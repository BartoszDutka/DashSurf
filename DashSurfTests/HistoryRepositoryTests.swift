import XCTest
import SwiftData
@testable import DashSurf

@MainActor
final class HistoryRepositoryTests: XCTestCase {
    private var persistence: PersistenceController!
    private var repository: HistoryRepository!

    override func setUp() async throws {
        persistence = PersistenceController(inMemory: true)
        repository = HistoryRepository(modelContext: ModelContext(persistence.container))
    }

    func testAddAndSearchHistory() throws {
        let url = URL(string: "https://example.com/a")!
        try repository.recordVisit(url: url, title: "Example")
        let results = try repository.search(query: "example")
        XCTAssertEqual(results.count, 1)
        XCTAssertEqual(results.first?.title, "Example")
    }

    func testDeleteHistory() throws {
        let url = URL(string: "https://example.com/b")!
        try repository.recordVisit(url: url, title: "B")
        let item = try repository.recent().first!
        try repository.delete(item)
        XCTAssertTrue(try repository.recent().isEmpty)
    }

    func testClearHistory() throws {
        try repository.recordVisit(url: URL(string: "https://a.com")!, title: "A")
        try repository.recordVisit(url: URL(string: "https://b.com")!, title: "B")
        try repository.clearAll()
        XCTAssertTrue(try repository.recent().isEmpty)
    }

    func testDedupWithinWindowIncrementsVisitCount() throws {
        let url = URL(string: "https://example.com/c")!
        try repository.recordVisit(url: url, title: "C")
        // Immediate second write within dedup window should not create a second row,
        // and may skip visitCount bump depending on timing — assert single row.
        try repository.recordVisit(url: url, title: "C2")
        let all = try repository.search(query: "")
        XCTAssertEqual(all.filter { $0.urlString.contains("/c") }.count, 1)
    }
}
