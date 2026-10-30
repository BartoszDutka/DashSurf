# CarPlay Compatibility — DashSurf

## Environment note

This document was written from public Apple documentation, WWDC materials, and the MIT-licensed [Cafari Lite](https://github.com/rPlayAI/cafari-lite) project. Physical CarPlay verification was **not** performed in the Windows authoring environment.

## What DashSurf uses

| Piece | API / mechanism | Status |
| --- | --- | --- |
| Phone browser | `WKWebView` + SwiftUI | Implemented |
| Persistent site data | `WKWebsiteDataStore.default()` | Implemented |
| Car scene declaration | `UIWindowSceneSessionRoleCarPlay` in Info.plist | Declared |
| Car scene role (Swift) | `UISceneSession.Role(rawValue: "UIWindowSceneSessionRoleCarPlay")` | Implemented |
| Car UI | Separate `WKWebView` in `CarPlayBrowserViewController` | Implemented (activates only if iOS creates the scene) |
| Shared logical state | `BrowserSessionManager` / `CarPlaySessionManager` | Implemented |
| Motion gate | Core Location speed heuristic (`CarMotionGate`) | Implemented (best-effort; not a CarPlay API) |
| Official CarPlay templates (`CPTemplate`) | CarPlay framework browsing templates | **Not** used as primary path |

## Entitlements required for the car window

From Apple’s CarPlay program and Cafari Lite’s verified notes:

- `com.apple.developer.carplay-video`
- `com.apple.developer.carplay-audio` (often required in practice for the app to appear on the head unit)

Request at: https://developer.apple.com/contact/carplay/

**Writing keys into an entitlements plist does not grant them.** Signing fails or the car scene never appears if Apple has not enabled the capability on your account/App ID.

Default DashSurf signing uses empty `DashSurf.entitlements` so clones build as a phone browser.

## Officially supported CarPlay Video direction (Apple)

Apple’s public CarPlay Video category expects:

1. Apps primarily providing video playback services
2. AirPlay video streaming support
3. Use of CarPlay framework templates for in-car browsing UI
4. Playback only when the vehicle indicates video is allowed (parked / supported hardware)

An unrestricted general-purpose web browser on CarPlay is **not** documented as a supported App Store category.

## What is available vs unavailable

### Available in DashSurf (phone)

Full browser, persistent sessions, history, bookmarks, tabs, Continue Watching, settings.

### Available when entitlements are granted and iOS creates the car scene

Car `UIWindowScene` with DashSurf’s car browser controller: Quick Access, Continue Watching list, load URLs, shared WebKit data store, motion overlay while driving (heuristic).

### Unavailable / not claimed

- Guaranteed App Store approval for WKWebView-on-CarPlay
- Private APIs or entitlement spoofing
- Sharing Safari’s cookie store with WKWebView
- DRM bypass for Netflix et al.
- Simulator validation of CarPlay entitlements (not supported)

### Not verified here

- Exact behavior on every iOS version / vehicle
- Whether Apple still creates `UIWindowSceneSessionRoleCarPlay` for newly granted video apps on the latest iOS
- Your account’s entitlement approval outcome

## How to verify on a physical device

1. Install a signed build on iPhone (Developer team + matching entitlements).
2. Confirm phone browser works (YouTube login → kill app → relaunch → still signed in).
3. Enable CarPlay entitlements only after Apple approval; resign with `CarPlay.entitlements`.
4. Connect wired/wireless CarPlay.
5. Check whether DashSurf appears on the head unit.
6. In Settings → CarPlay section, confirm connection status updates when the car scene connects.
7. Open a shortcut on the car screen; confirm cookies from the phone session apply (same data store).
8. Drive slowly / use motion: overlay should pause video when speed gate trips (if location allowed).

## References

- https://developer.apple.com/carplay/
- https://developer.apple.com/documentation/carplay/requesting-carplay-entitlements
- https://developer.apple.com/documentation/webkit/
- https://github.com/rPlayAI/cafari-lite (MIT)
