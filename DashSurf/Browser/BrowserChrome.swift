import SwiftUI
import UIKit

struct BrowserChrome: View {
    @Binding var address: String
    var progress: Double
    var isLoading: Bool
    var canGoBack: Bool
    var canGoForward: Bool
    var tabCount: Int
    var onSubmit: () -> Void
    var onBack: () -> Void
    var onForward: () -> Void
    var onReload: () -> Void
    var onTabs: () -> Void
    var onMenu: () -> Void
    var onFavorite: () -> Void

    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 10) {
                Button(action: onBack) {
                    Image(systemName: "chevron.left")
                }
                .disabled(!canGoBack)

                Button(action: onForward) {
                    Image(systemName: "chevron.right")
                }
                .disabled(!canGoForward)

                HStack {
                    Image(systemName: "lock.fill")
                        .font(.caption2)
                        .foregroundStyle(DashSurfTheme.secondaryText)
                    TextField("Search or enter website", text: $address)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                        .submitLabel(.go)
                        .onSubmit(onSubmit)
                    Button(action: onReload) {
                        Image(systemName: isLoading ? "xmark" : "arrow.clockwise")
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(DashSurfTheme.secondaryBackground, in: Capsule())

                Button(action: onFavorite) {
                    Image(systemName: "book")
                }
                Button(action: onTabs) {
                    Text("\(tabCount)")
                        .font(.caption.weight(.semibold))
                        .frame(width: 22, height: 22)
                        .overlay(RoundedRectangle(cornerRadius: 6).stroke(DashSurfTheme.primaryText, lineWidth: 1.5))
                }
                Button(action: onMenu) {
                    Image(systemName: "ellipsis")
                }
            }
            .foregroundStyle(DashSurfTheme.primaryText)
            .padding(.horizontal, 12)
            .padding(.top, 8)

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.clear)
                    Capsule()
                        .fill(DashSurfTheme.accent)
                        .frame(width: max(0, geo.size.width * progress))
                        .opacity(isLoading || progress > 0 && progress < 1 ? 1 : 0)
                }
            }
            .frame(height: 2)
            .padding(.horizontal, 16)
        }
        .background(DashSurfTheme.primaryBackground.opacity(0.96))
    }
}

struct TabsSheet: View {
    @ObservedObject var tabManager: TabManager
    @ObservedObject var session: BrowserSessionManager
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                ForEach(tabManager.tabs) { tab in
                    Button {
                        tabManager.selectTab(id: tab.id)
                        session.currentURL = tab.url
                        session.addressBarText = tab.url.isDashSurfHome ? "" : tab.url.absoluteString
                        dismiss()
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(tab.title).foregroundStyle(DashSurfTheme.primaryText)
                            Text(tab.url.absoluteString)
                                .font(.caption)
                                .foregroundStyle(DashSurfTheme.secondaryText)
                                .lineLimit(1)
                        }
                    }
                    .swipeActions {
                        Button(role: .destructive) {
                            session.webViewFactory.recycle(tabID: tab.id)
                            tabManager.closeTab(id: tab.id)
                        } label: {
                            Label("Close", systemImage: "xmark")
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(DashSurfTheme.primaryBackground)
            .navigationTitle("Tabs")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Close All") {
                        for tab in tabManager.tabs {
                            session.webViewFactory.recycle(tabID: tab.id)
                        }
                        tabManager.closeAll()
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        _ = tabManager.openNewTab(activate: true)
                        dismiss()
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}

struct ErrorBanner: View {
    let message: String
    var retry: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text(message)
                .multilineTextAlignment(.center)
                .foregroundStyle(DashSurfTheme.primaryText)
            Button("Try Again", action: retry)
                .buttonStyle(.borderedProminent)
                .tint(DashSurfTheme.accent)
        }
        .padding(20)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }
}

struct ShareSheet: UIViewControllerRepresentable {
    var items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
