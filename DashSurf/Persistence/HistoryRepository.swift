import Foundation
import SwiftData

@MainActor
final class HistoryRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func recordVisit(url: URL, title: String?, faviconURL: URL? = nil) throws {
        guard !url.isDashSurfHome else { return }
        guard url.scheme == "http" || url.scheme == "https" else { return }

        let normalized = URLService.normalizeForHistory(url)
        let urlString = normalized.absoluteString
        let domain = normalized.dashsurfDomain
        let now = Date()

        var descriptor = FetchDescriptor<BrowserHistoryItem>(
            predicate: #Predicate { $0.urlString == urlString },
            sortBy: [SortDescriptor(\.lastVisitedAt, order: .reverse)]
        )
        descriptor.fetchLimit = 1
        if let existing = try modelContext.fetch(descriptor).first {
            if now.timeIntervalSince(existing.lastVisitedAt) < AppConstants.historyDedupWindow {
                if let title, !title.isEmpty { existing.title = title }
                return
            }
            existing.visitCount += 1
            existing.lastVisitedAt = now
            if let title, !title.isEmpty { existing.title = title }
            if let faviconURL { existing.faviconURLString = faviconURL.absoluteString }
        } else {
            let item = BrowserHistoryItem(
                urlString: urlString,
                title: (title?.nilIfEmpty) ?? domain,
                domain: domain,
                faviconURLString: faviconURL?.absoluteString,
                firstVisitedAt: now,
                lastVisitedAt: now,
                visitCount: 1
            )
            modelContext.insert(item)
        }
        try modelContext.save()
    }

    func search(query: String, limit: Int = 200) throws -> [BrowserHistoryItem] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        var descriptor = FetchDescriptor<BrowserHistoryItem>(
            sortBy: [SortDescriptor(\.lastVisitedAt, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        let all = try modelContext.fetch(descriptor)
        guard !q.isEmpty else { return all }
        let lowered = q.lowercased()
        return all.filter {
            $0.title.lowercased().contains(lowered)
                || $0.urlString.lowercased().contains(lowered)
                || $0.domain.lowercased().contains(lowered)
        }
    }

    func recent(limit: Int = 20) throws -> [BrowserHistoryItem] {
        var descriptor = FetchDescriptor<BrowserHistoryItem>(
            sortBy: [SortDescriptor(\.lastVisitedAt, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        return try modelContext.fetch(descriptor)
    }

    func items(forDomain domain: String) throws -> [BrowserHistoryItem] {
        let d = domain.lowercased()
        let descriptor = FetchDescriptor<BrowserHistoryItem>(
            predicate: #Predicate { $0.domain == d },
            sortBy: [SortDescriptor(\.lastVisitedAt, order: .reverse)]
        )
        return try modelContext.fetch(descriptor)
    }

    func delete(_ item: BrowserHistoryItem) throws {
        modelContext.delete(item)
        try modelContext.save()
    }

    func deleteDomain(_ domain: String) throws {
        for item in try items(forDomain: domain) {
            modelContext.delete(item)
        }
        try modelContext.save()
    }

    func clearAll() throws {
        try modelContext.delete(model: BrowserHistoryItem.self)
        try modelContext.save()
    }

    func grouped(query: String = "") throws -> [(HistoryDateGroup, [BrowserHistoryItem])] {
        let items = try search(query: query, limit: 2000)
        var buckets: [HistoryDateGroup: [BrowserHistoryItem]] = [:]
        for item in items {
            let g = HistoryDateGroup.group(for: item.lastVisitedAt)
            buckets[g, default: []].append(item)
        }
        return HistoryDateGroup.allCases.compactMap { g in
            guard let list = buckets[g], !list.isEmpty else { return nil }
            return (g, list)
        }
    }
}
