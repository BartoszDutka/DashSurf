import Foundation

actor FaviconService {
    static func guessURL(for pageURL: URL) -> URL? {
        guard let host = pageURL.host else { return nil }
        return URL(string: "https://www.google.com/s2/favicons?domain=\(host)&sz=64")
    }

    func favicon(for pageURL: URL) async -> URL? {
        Self.guessURL(for: pageURL)
    }
}
