import Foundation

struct SearchService {
    func makeSearchURL(query: String, engine: SearchEngine) -> URL {
        engine.searchURL(for: query)
    }
}
