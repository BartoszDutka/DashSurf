import XCTest
import SwiftData
@testable import DashSurf

@MainActor
final class BookmarkRepositoryTests: XCTestCase {
    private var repository: BookmarkRepository!

    override func setUp() async throws {
        let persistence = PersistenceController(inMemory: true)
        repository = BookmarkRepository(modelContext: ModelContext(persistence.container))
    }

    func testAddUpdateDeleteBookmark() throws {
        let bookmark = try repository.add(title: "Apple", url: URL(string: "https://apple.com")!)
        XCTAssertEqual(try repository.all().count, 1)
        try repository.update(bookmark, title: "Apple Inc", url: URL(string: "https://www.apple.com")!, isFavorite: true)
        XCTAssertEqual(try repository.favorites().count, 1)
        try repository.delete(bookmark)
        XCTAssertTrue(try repository.all().isEmpty)
    }
}
