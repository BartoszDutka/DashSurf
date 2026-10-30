import SwiftUI

struct HistoryView: View {
    @ObservedObject var coordinator: AppCoordinator
    @EnvironmentObject private var dependencies: AppDependencies
    @State private var query = ""
    @State private var groups: [(HistoryDateGroup, [BrowserHistoryItem])] = []
    @State private var showClearConfirm = false

    var body: some View {
        NavigationStack {
            List {
                ForEach(groups, id: \.0) { group, items in
                    Section(group.rawValue) {
                        ForEach(items) { item in
                            Button {
                                coordinator.openInBrowser(item.url ?? AppConstants.defaultHomepage)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(item.title).foregroundStyle(DashSurfTheme.primaryText)
                                    Text(item.urlString)
                                        .font(.caption)
                                        .foregroundStyle(DashSurfTheme.secondaryText)
                                        .lineLimit(1)
                                }
                            }
                            .swipeActions {
                                Button(role: .destructive) {
                                    try? dependencies.historyRepository.delete(item)
                                    reload()
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
            .searchable(text: $query, prompt: "Search history")
            .onChange(of: query) { _, _ in reload() }
            .navigationTitle("History")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Clear", role: .destructive) { showClearConfirm = true }
                }
            }
            .alert("Clear all history?", isPresented: $showClearConfirm) {
                Button("Clear", role: .destructive) {
                    try? dependencies.historyRepository.clearAll()
                    reload()
                }
                Button("Cancel", role: .cancel) {}
            }
            .onAppear(perform: reload)
        }
    }

    private func reload() {
        groups = (try? dependencies.historyRepository.grouped(query: query)) ?? []
    }
}
