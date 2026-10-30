import SwiftUI
import UIKit

enum DashSurfTheme {
    static let primaryBackground = Color(hex: 0x0B0F17)
    static let secondaryBackground = Color(hex: 0x151B26)
    static let accent = Color(hex: 0x3186FF)
    static let primaryText = Color(hex: 0xFFFFFF)
    static let secondaryText = Color(hex: 0xA4ADBA)

    static var backgroundGradient: LinearGradient {
        LinearGradient(
            colors: [primaryBackground, secondaryBackground.opacity(0.95), primaryBackground],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}

extension Color {
    init(hex: UInt32, opacity: Double = 1) {
        let r = Double((hex >> 16) & 0xFF) / 255
        let g = Double((hex >> 8) & 0xFF) / 255
        let b = Double(hex & 0xFF) / 255
        self.init(.sRGB, red: r, green: g, blue: b, opacity: opacity)
    }
}
