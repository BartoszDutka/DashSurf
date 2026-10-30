import XCTest
@testable import DashSurf

final class URLServiceTests: XCTestCase {
    private let service = URLService()

    func testNormalizeURLDropsUTM() {
        let url = URL(string: "https://example.com/path?utm_source=x&id=1")!
        let normalized = URLService.normalizeForHistory(url)
        XCTAssertEqual(normalized.host, "example.com")
        XCTAssertTrue(normalized.query?.contains("id=1") == true)
        XCTAssertFalse(normalized.query?.contains("utm_source") == true)
    }

    func testResolveDomainAddsHTTPS() {
        let url = service.resolve("example.com", searchEngine: .google)
        XCTAssertEqual(url.absoluteString, "https://example.com")
    }

    func testResolveQueryUsesSearchEngine() {
        let url = service.resolve("swift concurrency", searchEngine: .google)
        XCTAssertTrue(url.absoluteString.contains("google.com/search"))
        XCTAssertTrue(url.absoluteString.contains("swift"))
    }

    func testGoogleSearchEncoding() {
        let url = SearchEngine.google.searchURL(for: "hello world")
        XCTAssertTrue(url.absoluteString.contains("hello"))
    }
}
