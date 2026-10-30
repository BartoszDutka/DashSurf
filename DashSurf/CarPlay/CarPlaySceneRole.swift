import UIKit

/// UIKit does not expose CarPlay window scene role as a typed Swift member.
/// The raw string matches Info.plist UIWindowSceneSessionRoleCarPlay.
/// Pattern documented by Apple scene manifests and used by MIT-licensed Cafari Lite.
enum CarPlaySceneRole {
    static let windowRole = UISceneSession.Role(rawValue: "UIWindowSceneSessionRoleCarPlay")
}
