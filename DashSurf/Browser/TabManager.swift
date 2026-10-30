import Foundation
import Combine

@MainActor
final class TabManager: ObservableObject {
    @Published private(set) var tabs: [BrowserTab] = []
    @Published private(set) var activeTabID: UUID?

    private let tabStateRepository: TabStateRepository
    private let settings: SettingsStore
    private var didRestore = false

    init(tabStateRepository: TabStateRepository, settings: SettingsStore) {
        self.tabStateRepository = tabStateRepository
        self.settings = settings
    }

    var activeTab: BrowserTab? {
        tabs.first(where: { $0.id == activeTabID }) ?? tabs.first
    }

    func restoreIfNeeded() {
        guard !didRestore else { return }
        didRestore = true
        if settings.restoreTabsOnLaunch, let saved = try? tabStateRepository.load(), !saved.isEmpty {
            tabs = saved
            activeTabID = saved.first(where: \.isActive)?.id ?? saved.first?.id
        } else {
            let tab = BrowserTab.fresh(isActive: true)
            tabs = [tab]
            activeTabID = tab.id
            persist()
        }
    }

    @discardableResult
    func openNewTab(url: URL? = nil, activate: Bool = true) -> BrowserTab {
        var tab = BrowserTab.fresh(isActive: activate)
        if let url {
            tab.url = url
            tab.title = url.dashsurfDomain.isEmpty ? "New Tab" : url.dashsurfDomain
        }
        if activate {
            tabs = tabs.map { var t = $0; t.isActive = false; return t }
            tab.isActive = true
            activeTabID = tab.id
        }
        tabs.append(tab)
        persist()
        return tab
    }

    func closeTab(id: UUID) {
        tabs.removeAll { $0.id == id }
        if tabs.isEmpty {
            let tab = BrowserTab.fresh(isActive: true)
            tabs = [tab]
            activeTabID = tab.id
        } else if activeTabID == id {
            activeTabID = tabs.last?.id
            tabs = tabs.map { var t = $0; t.isActive = (t.id == activeTabID); return t }
        }
        persist()
    }

    func closeAll() {
        let tab = BrowserTab.fresh(isActive: true)
        tabs = [tab]
        activeTabID = tab.id
        persist()
    }

    func selectTab(id: UUID) {
        activeTabID = id
        let now = Date()
        tabs = tabs.map { tab in
            var t = tab
            t.isActive = (t.id == id)
            if t.isActive { t.lastActiveAt = now }
            return t
        }
        persist()
    }

    func updateActive(url: URL?, title: String?) {
        guard let activeTabID else { return }
        tabs = tabs.map { tab in
            guard tab.id == activeTabID else { return tab }
            var t = tab
            if let url { t.url = url }
            if let title, !title.isEmpty { t.title = title }
            t.lastActiveAt = Date()
            return t
        }
        persist()
    }

    func persist() {
        try? tabStateRepository.save(tabs)
    }
}
