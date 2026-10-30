import XCTest
@testable import DashSurf

final class MediaDetectionTests: XCTestCase {
    func testDetectYouTube() {
        let service = MediaDetectionService()
        let url = URL(string: "https://www.youtube.com/watch?v=abcdefghijk")!
        let media = service.detect(url: url, pageTitle: "Test")
        XCTAssertEqual(media?.provider, "YouTube")
        XCTAssertNotNil(media?.thumbnailURL)
    }

    func testIgnorePlainHomepage() {
        let service = MediaDetectionService()
        let url = URL(string: "https://www.youtube.com/")!
        XCTAssertNil(service.detect(url: url, pageTitle: "YouTube"))
    }
}
