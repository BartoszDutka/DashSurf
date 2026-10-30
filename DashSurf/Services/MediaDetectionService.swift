import Foundation

struct DetectedMedia: Equatable {
    var url: URL
    var title: String
    var provider: String
    var thumbnailURL: URL?
}

struct MediaDetectionService {
    func detect(url: URL, pageTitle: String?) -> DetectedMedia? {
        let host = url.host?.lowercased() ?? ""
        let path = url.path.lowercased()

        if host.contains("youtube.com") || host == "youtu.be" {
            if path.contains("/watch") || host == "youtu.be" || path.contains("/shorts/") {
                let id = youtubeID(from: url)
                let thumb = id.flatMap { URL(string: "https://i.ytimg.com/vi/\($0)/hqdefault.jpg") }
                return DetectedMedia(
                    url: url,
                    title: pageTitle?.nilIfEmpty ?? "YouTube",
                    provider: "YouTube",
                    thumbnailURL: thumb
                )
            }
            return nil
        }

        if host.contains("twitch.tv") {
            if path.split(separator: "/").count >= 1 && !path.contains("/directory") {
                return DetectedMedia(
                    url: url,
                    title: pageTitle?.nilIfEmpty ?? "Twitch",
                    provider: "Twitch",
                    thumbnailURL: nil
                )
            }
            return nil
        }

        if host.contains("vimeo.com") {
            return DetectedMedia(
                url: url,
                title: pageTitle?.nilIfEmpty ?? "Vimeo",
                provider: "Vimeo",
                thumbnailURL: nil
            )
        }

        if host.contains("netflix.com") && (path.contains("/watch") || path.contains("/title")) {
            // DRM may block WKWebView playback; we still remember the page for Continue Watching.
            return DetectedMedia(
                url: url,
                title: pageTitle?.nilIfEmpty ?? "Netflix",
                provider: "Netflix",
                thumbnailURL: nil
            )
        }

        return nil
    }

    private func youtubeID(from url: URL) -> String? {
        if url.host?.contains("youtu.be") == true {
            return url.pathComponents.dropFirst().first
        }
        if let comps = URLComponents(url: url, resolvingAgainstBaseURL: false),
           let v = comps.queryItems?.first(where: { $0.name == "v" })?.value {
            return v
        }
        let parts = url.path.split(separator: "/")
        if let shortsIndex = parts.firstIndex(of: "shorts"), parts.indices.contains(shortsIndex + 1) {
            return String(parts[shortsIndex + 1])
        }
        return nil
    }
}
