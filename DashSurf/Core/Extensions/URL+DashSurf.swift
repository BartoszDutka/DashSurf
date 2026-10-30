import Foundation

extension URL {
    var dashsurfDomain: String {
        host?.lowercased() ?? ""
    }

    var isDashSurfHome: Bool {
        absoluteString == "about:home" || scheme == "about"
    }
}

extension String {
    var nilIfEmpty: String? {
        let t = trimmingCharacters(in: .whitespacesAndNewlines)
        return t.isEmpty ? nil : t
    }
}
