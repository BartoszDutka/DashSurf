import SwiftUI

struct RecentMediaView: View {
    @EnvironmentObject private var dependencies: AppDependencies
    @State private var items: [RecentMediaItem] = []

    var body: some View {
        List {
            ForEach(items) { item in
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.title)
                    Text("\(item.provider) · \(item.urlString)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
        }
        .onAppear {
            items = (try? dependencies.recentMediaRepository.recent()) ?? []
        }
    }
}
