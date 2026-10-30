import Foundation

struct URLService {
    func resolve(_ input: String, searchEngine: SearchEngine) -> URL {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return AppConstants.defaultHomepage }

        if trimmed == "about:home" {
            return AppConstants.defaultHomepage
        }

        if let url = URL(string: trimmed), url.scheme != nil, url.host != nil {
            return url
        }

        if looksLikeDomain(trimmed) {
            let withScheme = trimmed.hasPrefix("//") ? "https:\(trimmed)" : "https://\(trimmed)"
            if let url = URL(string: withScheme) {
                return url
            }
        }

        return searchEngine.searchURL(for: trimmed)
    }

    private func looksLikeDomain(_ value: String) -> Bool {
        if value.contains(" ") { return false }
        if value.contains("/") { return true }
        return value.contains(".") && !value.hasPrefix(".")
    }

    static func normalizeForHistory(_ url: URL) -> URL {
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return url
        }
        components.fragment = nil
        // Drop common tracking params without rewriting meaningful paths.
        let drop: Set<String> = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"]
        if let items = components.queryItems {
            let filtered = items.filter { item in
                !drop.contains(item.name.lowercased())
            }
            components.queryItems = filtered.isEmpty ? nil : filtered
        }
        return components.url ?? url
    }
}
