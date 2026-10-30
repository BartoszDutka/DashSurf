import Foundation

enum HistoryDateGroup: String, CaseIterable, Identifiable {
    case today = "Today"
    case yesterday = "Yesterday"
    case last7Days = "Last 7 Days"
    case older = "Older"

    var id: String { rawValue }

    static func group(for date: Date, now: Date = Date(), calendar: Calendar = .current) -> HistoryDateGroup {
        if calendar.isDateInToday(date) { return .today }
        if calendar.isDateInYesterday(date) { return .yesterday }
        if let weekAgo = calendar.date(byAdding: .day, value: -7, to: now), date >= weekAgo {
            return .last7Days
        }
        return .older
    }
}
