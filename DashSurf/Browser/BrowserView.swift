import SwiftUI
import UIKit

struct BrowserContainerView: View {
    @ObservedObject var coordinator: AppCoordinator
    @EnvironmentObject private var session: BrowserSessionManager
    @EnvironmentObject private var tabManager: TabManager
    @StateObject private var viewModel: BrowserViewModel

    init(coordinator: AppCoordinator) {
        self.coordinator = coordinator
        // Temporary placeholder; replaced in onAppear with real deps via StateObject workaround below.
        _viewModel = StateObject(wrappedValue: BrowserViewModel(
            session: AppDependencies.shared.sessionManager,
            tabManager: AppDependencies.shared.tabManager
        ))
    }

    var body: some View {
        BrowserView(viewModel: viewModel)
    }
}

struct BrowserView: View {
    @ObservedObject var viewModel: BrowserViewModel
    @EnvironmentObject private var session: BrowserSessionManager
    @EnvironmentObject private var tabManager: TabManager
    @EnvironmentObject private var settings: SettingsStore
    @EnvironmentObject private var carPlay: CarPlayAvailabilityService
    @State private var showShare = false
    @State private var showClearDomainConfirm = false

    var body: some View {
        VStack(spacing: 0) {
            BrowserChrome(
                address: $session.addressBarText,
                progress: session.estimatedProgress,
                isLoading: session.isLoading,
                canGoBack: session.canGoBack,
                canGoForward: session.canGoForward,
                tabCount: tabManager.tabs.count,
                onSubmit: { session.submitAddressBar() },
                onBack: viewModel.goBack,
                onForward: viewModel.goForward,
                onReload: viewModel.reloadOrStop,
                onTabs: { viewModel.showTabsSheet = true },
                onMenu: { viewModel.showMenu = true },
                onFavorite: {
                    _ = try? session.addBookmarkForCurrentPage()
                }
            )

            ZStack {
                if let activeID = tabManager.activeTabID {
                    WebViewRepresentable(tabID: activeID, session: session)
                        .id(activeID)
                } else {
                    Color(DashSurfTheme.primaryBackground)
                }

                if let message = session.errorMessage {
                    ErrorBanner(message: message) {
                        session.errorMessage = nil
                        viewModel.reloadOrStop()
                    }
                    .padding()
                }
            }
        }
        .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
        .sheet(isPresented: $viewModel.showTabsSheet) {
            TabsSheet(tabManager: tabManager, session: session)
        }
        .confirmationDialog("Browser Menu", isPresented: $viewModel.showMenu, titleVisibility: .visible) {
            Button("New Tab") { _ = tabManager.openNewTab(activate: true) }
            Button("Add Bookmark") { _ = try? session.addBookmarkForCurrentPage() }
            Button("Share") { showShare = true }
            Button("Copy Link") {
                UIPasteboard.general.string = session.currentURL.absoluteString
            }
            Button("Open in Safari") {
                UIApplication.shared.open(session.currentURL)
            }
            Button(session.desktopMode ? "Mobile Site" : "Desktop Site") {
                session.toggleDesktopMode()
            }
            if carPlay.isCarSceneConnected {
                Button("Send to CarPlay") {
                    AppDependencies.shared.carPlaySession.sendActivePageToCar()
                }
            }
            Button("Clear Website Data for Domain", role: .destructive) {
                showClearDomainConfirm = true
            }
            Button("Cancel", role: .cancel) {}
        }
        .sheet(isPresented: $showShare) {
            if let url = viewModel.shareCurrent() {
                ShareSheet(items: [url])
            }
        }
        .alert("Clear data for \(session.currentURL.dashsurfDomain)?", isPresented: $showClearDomainConfirm) {
            Button("Clear", role: .destructive) {
                let domain = session.currentURL.dashsurfDomain
                Task {
                    await AppDependencies.shared.websiteDataService.clearData(forDomain: domain)
                }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Removes cookies and site data for this domain from DashSurf. Safari data is not affected.")
        }
    }
}
