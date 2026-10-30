#!/usr/bin/env python3
"""Generate all DashSurf sources, then regenerate the Xcode project."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    emit = load("emit", ROOT / "tools" / "_emit.py")
    rest = load("emit_rest", ROOT / "tools" / "_emit_rest.py")
    browser = load("emit_browser", ROOT / "tools" / "_emit_browser.py")
    features = load("emit_features", ROOT / "tools" / "_emit_features.py")
    carplay = load("emit_carplay", ROOT / "tools" / "_emit_carplay_ui.py")

    print("=== App / Core / Models ===")
    emit.write_app()
    emit.write_core()
    emit.write_models()

    print("=== Persistence / Services ===")
    rest.write_persistence()
    rest.write_services()

    print("=== Browser ===")
    browser.write_browser()

    print("=== Features ===")
    features.write_features()

    print("=== CarPlay / UI / Assets / Tests ===")
    carplay.write_carplay()
    carplay.write_ui()
    carplay.write_assets()
    carplay.write_tests()

    print("=== Docs ===")
    write_docs()

    print("=== Xcode project ===")
    gen = load("generate_project", ROOT / "tools" / "generate_project.py")
    gen.main()

    swift_count = len(list((ROOT / "DashSurf").rglob("*.swift")))
    test_count = len(list((ROOT / "DashSurfTests").rglob("*.swift")))
    print(f"Swift app files: {swift_count}")
    print(f"Swift test files: {test_count}")


def write_docs() -> None:
    (ROOT / "README.md").write_text(README, encoding="utf-8")
    (ROOT / "CARPLAY_COMPATIBILITY.md").write_text(CARPLAY, encoding="utf-8")
    (ROOT / "docs" / "MANUAL_TEST_PLAN.md").write_text(MANUAL, encoding="utf-8")
    print("  README.md")
    print("  CARPLAY_COMPATIBILITY.md")
    print("  docs/MANUAL_TEST_PLAN.md")


README = r'''# DashSurf

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
'''

CARPLAY = r'''# CarPlay Compatibility — DashSurf

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
'''

MANUAL = r'''# DashSurf manual test plan

Run on a physical iPhone. Mark each item only after you observe it.

## Phone browser

- [ ] Cold launch shows Home with Quick Access defaults
- [ ] Search field opens Browser with Google results
- [ ] Enter `https://example.com` loads the site
- [ ] Back / Forward / Reload / Stop work
- [ ] Progress bar appears while loading
- [ ] New Tab / Close Tab / Tab switch work
- [ ] Kill app → relaunch → tabs restore (if setting enabled)
- [ ] Add bookmark → appears in Bookmarks / Favorites
- [ ] History records visits and groups by day
- [ ] Share / Copy Link / Open in Safari work
- [ ] Desktop Site toggles content mode
- [ ] Clear Website Data for domain signs out that site in DashSurf
- [ ] Offline / invalid URL shows an error, TLS failures are not bypassed

## Persistent login

- [ ] Sign in to a site that allows WebView login
- [ ] Force-quit DashSurf → relaunch → still signed in
- [ ] Reboot iPhone → still signed in
- [ ] If Google blocks WebView, Open in Safari is available

## Continue Watching

- [ ] Open a YouTube watch URL
- [ ] Item appears under Continue Watching
- [ ] Tapping it reopens the URL

## CarPlay (only with granted entitlements)

- [ ] App appears on head unit
- [ ] Shortcuts / Continue Watching open pages
- [ ] Session cookies shared with phone WebKit store
- [ ] Motion gate overlays when moving (if location allowed)

## Honesty

Do not check items that were not actually tested. Authoring environment did not run these.
'''


if __name__ == "__main__":
    main()
