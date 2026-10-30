import Foundation

enum AppConstants {
    static let appName = "DashSurf"
    static let slogan = "Your browser. Your screen. Your way."
    static let bundleFallbackID = "com.example.dashsurf"
    static let maxLiveWebViews = 4
    static let historyDedupWindow: TimeInterval = 8
    static let defaultHomepage = URL(string: "about:home")!
}

enum DashSurfNotification {
    static let carPlayConnected = Notification.Name("DashSurf.CarPlayConnected")
    static let carPlayDisconnected = Notification.Name("DashSurf.CarPlayDisconnected")
    static let sendURLToCarPlay = Notification.Name("DashSurf.SendURLToCarPlay")
    static let accountSessionMayHaveChanged = Notification.Name("DashSurf.AccountSessionMayHaveChanged")
    static let openURLFromCarPlay = Notification.Name("DashSurf.OpenURLFromCarPlay")
}
