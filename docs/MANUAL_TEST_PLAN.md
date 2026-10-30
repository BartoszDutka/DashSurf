# DashSurf manual test plan

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
