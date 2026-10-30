# DashSurf

**Your browser. Your screen. Your way.**

DashSurf is a native iOS browser and multimedia companion for iPhone, designed with optional Apple CarPlay integration when Apple grants the required entitlements.

It focuses on durable browsing sessions, history, bookmarks, tab restore, Continue Watching, and local-only data — without requiring a DashSurf account or backend.

> This repository was authored on Windows. **Build and run on macOS with Xcode.** Compilation was not executed in the authoring environment.

## Features

- Full WKWebView browser (tabs, address bar, desktop/mobile mode, share, Open in Safari)
- Persistent logins via `WKWebsiteDataStore.default()` (cookies / localStorage retained across launches)
- Browsing history with search, domain filter, Today / Yesterday / Last 7 Days / Older grouping
- Bookmarks, favorites, folders-ready model, Quick Access shortcuts
- Continue Watching for detected media URLs (YouTube, Twitch, etc.)
- Tab restore after relaunch
- Settings: appearance, search engine, privacy clears, CarPlay status
- Optional CarPlay window scene (`UIWindowSceneSessionRoleCarPlay`) when entitlements are granted

## Technologies

- Swift 5, SwiftUI + UIKit, WebKit, SwiftData, AVFoundation, CarPlay-related scene APIs
- Architecture: MVVM + Repository + Dependency Injection (`AppDependencies`)
- Concurrency: async/await, `@MainActor` where UI-bound

## Architecture

```
DashSurf/
  App/           Entry, scenes, root tabs
  Browser/       WKWebView, tabs, session
  CarPlay/       Optional car window + availability
  Features/      Home, History, Bookmarks, Settings, …
  Models/        SwiftData models
  Persistence/   Repositories
  Services/      URL, search, favicon, media, website data
  UI/Theme/      Colors / styling
```

## System requirements

- macOS with Xcode 15+ (recommended Xcode 16)
- iOS 17.0+ deployment target
- Physical iPhone for cookie/session and CarPlay testing
- Paid Apple Developer account required for device install and CarPlay entitlements

## Open & run (Mac)

1. Copy the `DashSurf` folder to your Mac (or clone the repo).
2. Open `DashSurf.xcodeproj` in Xcode.
3. Select the **DashSurf** target → **Signing & Capabilities**.
4. Choose your Team. Change `PRODUCT_BUNDLE_IDENTIFIER` from `com.example.dashsurf` if needed.
5. Select your iPhone and press Run.

Optional: copy `Local.xcconfig.example` → `Local.xcconfig` and fill team / bundle id.

### Regenerate the Xcode project

If you add/remove Swift files:

```bash
python3 tools/run_emit.py          # only if regenerating sources from emitters
python3 tools/generate_project.py  # rebuild project.pbxproj from the source tree
```

## Signing

- Default entitlements file: `DashSurf/DashSurf.entitlements` (empty — phone browser only).
- After Apple grants CarPlay capabilities, point `CODE_SIGN_ENTITLEMENTS` to `DashSurf/CarPlay.entitlements`.
- Do not invent Team IDs or provisioning profiles. Xcode Automatic Signing is fine for personal use.

## Testing

### Unit tests (Mac / Xcode)

Product → Test, or:

```bash
xcodebuild test -scheme DashSurf -destination 'platform=iOS Simulator,name=iPhone 16'
```

Covered areas include URL normalization, history CRUD, bookmarks, tabs, recent media, media detection, settings.

### Manual tests

See `docs/MANUAL_TEST_PLAN.md`. Session persistence and CarPlay require a physical device.

**Not run in the authoring environment:** Xcode build, Simulator, device install, CarPlay.

## CarPlay configuration

1. Request entitlements: https://developer.apple.com/contact/carplay/
2. Ask for **CarPlay Video** and typically also **CarPlay Audio** (both are often required for the car window scene to appear).
3. Enable capabilities on your App ID and regenerate the provisioning profile.
4. Sign with `CarPlay.entitlements`.
5. Connect a supported vehicle or CarPlay-capable head unit. Simulator cannot validate CarPlay entitlements.

Details: [CARPLAY_COMPATIBILITY.md](./CARPLAY_COMPATIBILITY.md).

## WebKit limitations

- Google / some OAuth providers may block embedded WebView login — use **Open in Safari**.
- DashSurf does **not** share Safari’s cookie jar with `WKWebView`.
- Do not disable TLS validation.
- `window.open` / `target=_blank` open as new DashSurf tabs.

## DRM limitations

- Netflix and other DRM/FairPlay services often refuse playback inside `WKWebView`.
- DashSurf may still remember the page in Continue Watching and offer Open in Safari / the official app.
- No stream ripping, DRM bypass, or password capture is implemented.

## Google login limitations

Embedded WebViews are frequently blocked for Google accounts. This is intentional provider policy, not a DashSurf bug. Prefer Safari when challenged.

## Known issues / honesty

- CarPlay window requires Apple-granted entitlements; default builds are phone-only.
- `UIWindowSceneSessionRoleCarPlay` hosting arbitrary UIKit (including WKWebView) is used by open projects such as Cafari Lite (MIT) and may change in future iOS releases.
- Official App Store CarPlay Video apps are expected to use CarPlay framework templates + AirPlay; unrestricted browser UX may not pass App Review.
- App icon is a generated placeholder; replace with a polished design asset before distribution.
- Unit tests were authored but not executed here (no macOS/Xcode in the authoring environment).

## Roadmap

- Folder management UI for bookmarks
- Stronger media position persistence where sites allow it legally
- Official CarPlay template browsing UI if/when entitlements + review path fit
- iCloud sync (optional, user-controlled)
- Reader mode / content blockers

## License notes

DashSurf original code: use privately as you wish; add a LICENSE file before publishing.

Reference: [Cafari Lite](https://github.com/rPlayAI/cafari-lite) (MIT) — scene-role concept and entitlement documentation. APTV inspired the product idea only; its repo does not license app source for reuse.
