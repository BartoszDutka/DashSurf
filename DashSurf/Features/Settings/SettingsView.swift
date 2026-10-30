import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var settings: SettingsStore
    @EnvironmentObject private var dependencies: AppDependencies
    @EnvironmentObject private var carPlay: CarPlayAvailabilityService
    @State private var confirmClearHistory = false
    @State private var confirmClearCookies = false
    @State private var confirmClearMedia = false
    @State private var statusMessage: String?

    var body: some View {
        NavigationStack {
            List {
                Section("General") {
                    Picker("Appearance", selection: $settings.colorSchemePreference) {
                        ForEach(AppearancePreference.allCases) { pref in
                            Text(pref.title).tag(pref)
                        }
                    }
                    Picker("Default Search Engine", selection: $settings.searchEngine) {
                        ForEach(SearchEngine.allCases) { engine in
                            Text(engine.title).tag(engine)
                        }
                    }
                    TextField("Homepage", text: $settings.homepageURLString)
                        .textInputAutocapitalization(.never)
                    Toggle("Restore Tabs on Launch", isOn: $settings.restoreTabsOnLaunch)
                    Toggle("Desktop Mode Default", isOn: $settings.desktopModeDefault)
                }

                Section("Privacy") {
                    Toggle("Enable History Recording", isOn: $settings.historyRecordingEnabled)
                    Button("Clear History", role: .destructive) { confirmClearHistory = true }
                    Button("Clear Cookies & Website Data", role: .destructive) { confirmClearCookies = true }
                    Button("Clear Recent Media", role: .destructive) { confirmClearMedia = true }
                    NavigationLink("Edit Quick Access") {
                        QuickAccessEditorView()
                    }
                }

                Section("CarPlay") {
                    LabeledContent("Connection") {
                        Text(carPlay.connectionLabel)
                            .foregroundStyle(DashSurfTheme.secondaryText)
                    }
                    LabeledContent("Availability") {
                        Text(carPlay.status.summary)
                            .foregroundStyle(DashSurfTheme.secondaryText)
                            .multilineTextAlignment(.trailing)
                    }
                    ForEach(carPlay.capabilityNotes, id: \.self) { note in
                        Text(note)
                            .font(.footnote)
                            .foregroundStyle(DashSurfTheme.secondaryText)
                    }
                    NavigationLink("Compatibility Details") {
                        CarPlayCompatibilityInfoView()
                    }
                }

                Section("About") {
                    LabeledContent("DashSurf", value: AppConstants.slogan)
                    LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0")
                    NavigationLink("Licenses") { LicensesView() }
                    NavigationLink("Privacy Information") { PrivacyInfoView() }
                }

                if let statusMessage {
                    Section {
                        Text(statusMessage).foregroundStyle(DashSurfTheme.accent)
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
            .navigationTitle("Settings")
            .alert("Clear browsing history?", isPresented: $confirmClearHistory) {
                Button("Clear", role: .destructive) {
                    try? dependencies.historyRepository.clearAll()
                    statusMessage = "History cleared."
                }
                Button("Cancel", role: .cancel) {}
            }
            .alert("Clear cookies and website data?", isPresented: $confirmClearCookies) {
                Button("Clear", role: .destructive) {
                    Task {
                        await dependencies.websiteDataService.clearAllWebsiteData()
                        statusMessage = "Website data cleared. You will be signed out of sites."
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This signs you out of websites inside DashSurf. Safari is not affected.")
            }
            .alert("Clear Continue Watching?", isPresented: $confirmClearMedia) {
                Button("Clear", role: .destructive) {
                    try? dependencies.recentMediaRepository.clearAll()
                    statusMessage = "Recent media cleared."
                }
                Button("Cancel", role: .cancel) {}
            }
        }
    }
}

struct CarPlayCompatibilityInfoView: View {
    var body: some View {
        ScrollView {
            Text(CarPlayCompatibilityCopy.summary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
        }
        .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
        .navigationTitle("CarPlay")
    }
}

struct LicensesView: View {
    var body: some View {
        ScrollView {
            Text(
                """
                DashSurf is original software.

                Architectural reference (MIT): Cafari Lite by rPlayAI — concepts for UIWindowSceneSessionRoleCarPlay scene wiring. No source was copied verbatim beyond publicly documented scene role strings and entitlement key names.

                APTV (Kimentanm/aptv) was used only as a product inspiration. Its repository has no open-source license for app code reuse; nothing from APTV was copied.

                Apple frameworks (WebKit, SwiftUI, SwiftData, CarPlay, AVFoundation) remain Apple property and are used via public APIs only.
                """
            )
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
        .navigationTitle("Licenses")
    }
}

struct PrivacyInfoView: View {
    var body: some View {
        ScrollView {
            Text(
                """
                DashSurf stores browsing history, bookmarks, tabs, quick access shortcuts and Continue Watching metadata locally on your device using SwiftData.

                Website cookies and localStorage are stored by WebKit through WKWebsiteDataStore.default(). DashSurf does not operate an account server and does not upload your history.

                Passwords are never captured by DashSurf. Use the site’s own login forms. Google and other providers may block embedded WebView sign-in; use Open in Safari when prompted.

                Location permission (optional) is only used to estimate whether the car is moving so car-screen video can be paused while driving. Coordinates are not stored or transmitted.
                """
            )
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .background(DashSurfTheme.primaryBackground.ignoresSafeArea())
        .navigationTitle("Privacy")
    }
}

enum CarPlayCompatibilityCopy {
    static let summary = """
    DashSurf’s phone browser does not require CarPlay entitlements.

    Optional car window support uses UIWindowSceneSessionRoleCarPlay (documented scene role string). Apple must grant com.apple.developer.carplay-video and typically also com.apple.developer.carplay-audio before iOS will create that scene.

    Request entitlements at https://developer.apple.com/contact/carplay/ then sign with CarPlay.entitlements.

    Official CarPlay Video apps (CarPlay framework templates + AirPlay) are a separate, App Review–oriented path. Arbitrary unrestricted browsing on the head unit is not guaranteed by Apple and may change across iOS releases.

    See CARPLAY_COMPATIBILITY.md in the repository for full details.
    """
}
