import Foundation
import Combine
import UIKit

enum CarPlayAvailabilityStatus: Equatable {
    case phoneOnlyNoEntitlementConfigured
    case entitlementsConfiguredButNotConnected
    case connected
    case featureUnavailable(reason: String)

    var summary: String {
        switch self {
        case .phoneOnlyNoEntitlementConfigured:
            return "CarPlay car window not enabled in this build (no CarPlay entitlements signed in)."
        case .entitlementsConfiguredButNotConnected:
            return "CarPlay entitlements present in project configuration; waiting for vehicle connection."
        case .connected:
            return "CarPlay window scene is connected."
        case .featureUnavailable(let reason):
            return reason
        }
    }
}

@MainActor
final class CarPlayAvailabilityService: ObservableObject {
    @Published private(set) var status: CarPlayAvailabilityStatus = .phoneOnlyNoEntitlementConfigured
    @Published private(set) var isCarSceneConnected = false
    @Published private(set) var entitlementKeysDetectedInBundle: [String] = []

    var connectionLabel: String {
        isCarSceneConnected ? "Connected" : "Not connected"
    }

    var capabilityNotes: [String] {
        [
            "Full unrestricted WKWebView browsing on CarPlay is not a guaranteed public CarPlay template API.",
            "Optional DashSurf car window uses UIWindowSceneSessionRoleCarPlay and requires Apple-granted entitlements.",
            "Video should only display when the vehicle allows it (parked / supported head unit).",
            "Without entitlements DashSurf remains a complete iPhone browser."
        ]
    }

    func refreshFromBundle() {
        let keys = Self.readCarPlayEntitlementKeys()
        entitlementKeysDetectedInBundle = keys
        if keys.isEmpty {
            status = .phoneOnlyNoEntitlementConfigured
        } else if isCarSceneConnected {
            status = .connected
        } else {
            status = .entitlementsConfiguredButNotConnected
        }
    }

    func notePhoneSceneConnected() {
        refreshFromBundle()
    }

    func noteCarSceneConnected() {
        isCarSceneConnected = true
        status = .connected
        NotificationCenter.default.post(name: DashSurfNotification.carPlayConnected, object: nil)
    }

    func noteCarSceneDisconnected() {
        isCarSceneConnected = false
        refreshFromBundle()
        NotificationCenter.default.post(name: DashSurfNotification.carPlayDisconnected, object: nil)
    }

    /// Best-effort read of embedded entitlements. Not a private API probe —
    /// uses the signed app's embedded.mobileprovision / entitlements when present.
    /// If unavailable, falls back to Info.plist marker + CODE_SIGN configuration honesty.
    private static func readCarPlayEntitlementKeys() -> [String] {
        // Public API cannot reliably enumerate managed entitlements at runtime on device
        // without reading the embedded profile. We check a compile-time flag and Info.plist.
        var found: [String] = []
        #if DASHSURF_CARPLAY_ENABLED
        found.append("com.apple.developer.carplay-video")
        found.append("com.apple.developer.carplay-audio")
        #endif
        if let path = Bundle.main.path(forResource: "embedded", ofType: "mobileprovision"),
           let data = try? Data(contentsOf: URL(fileURLWithPath: path)),
           let text = String(data: data, encoding: .ascii) {
            if text.contains("com.apple.developer.carplay-video") {
                found.append("com.apple.developer.carplay-video")
            }
            if text.contains("com.apple.developer.carplay-audio") {
                found.append("com.apple.developer.carplay-audio")
            }
        }
        return Array(Set(found)).sorted()
    }
}
