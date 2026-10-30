import SwiftUI

struct QuickAccessEditorView: View {
    @EnvironmentObject private var dependencies: AppDependencies
    @State private var items: [QuickAccessItem] = []
    @State private var showAdd = false
    @State private var title = ""
    @State private var urlString = ""

    var body: some View {
        List {
            ForEach(items) { item in
                HStack {
                    Image(systemName: item.symbolName)
                    VStack(alignment: .leading) {
                        Text(item.title)
                        Text(item.urlString).font(.caption).foregroundStyle(.secondary)
                    }
                }
                .swipeActions {
                    Button(role: .destructive) {
                        try? dependencies.quickAccessRepository.delete(item)
                        reload()
                    } label: { Label("Delete", systemImage: "trash") }
                    Button {
                        try? dependencies.quickAccessRepository.togglePin(item)
                        reload()
                    } label: { Label("Pin", systemImage: "pin") }
                }
            }
            .onMove { source, dest in
                items.move(fromOffsets: source, toOffset: dest)
                try? dependencies.quickAccessRepository.reorder(items)
            }
        }
        .navigationTitle("Quick Access")
        .toolbar {
            EditButton()
            Button { showAdd = true } label: { Image(systemName: "plus") }
        }
        .sheet(isPresented: $showAdd) {
            Form {
                TextField("Name", text: $title)
                TextField("URL", text: $urlString)
                Button("Add") {
                    if let url = URL(string: urlString) {
                        _ = try? dependencies.quickAccessRepository.add(title: title, url: url)
                        reload()
                    }
                    showAdd = false
                }
            }
        }
        .onAppear(perform: reload)
    }

    private func reload() {
        items = (try? dependencies.quickAccessRepository.all()) ?? []
    }
}
