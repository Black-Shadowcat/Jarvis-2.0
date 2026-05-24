import SwiftUI

// Zentrale Farbdefinitionen - 1:1 aus health.html uebernommen
enum HUDColor {
    static let background   = Color(red: 0.039, green: 0.055, blue: 0.153)  // #0a0e27
    static let backgroundAlt = Color(red: 0.102, green: 0.122, blue: 0.227) // #1a1f3a
    static let panelBg      = Color(red: 0.039, green: 0.055, blue: 0.153).opacity(0.6)
    static let panelBorder  = Color(red: 0, green: 1, blue: 0.533).opacity(0.15) // rgba(0,255,136,0.15)

    static let green  = Color(red: 0,     green: 1,     blue: 0.533)  // #00ff88
    static let blue   = Color(red: 0.165, green: 0.620, blue: 0.886)  // #2a9ee2
    static let red    = Color(red: 1,     green: 0.200, blue: 0.400)  // #ff3366
    static let orange = Color(red: 1,     green: 0.420, blue: 0)      // #ff6b00
    static let gray   = Color(red: 0.533, green: 0.533, blue: 0.533)  // #888888

    static let text     = Color(red: 0,     green: 1,     blue: 0.533)  // #00ff88
    static let textDim  = Color(red: 0.667, green: 0.667, blue: 0.667)  // #aaaaaa
    static let textMuted = Color(red: 0.400, green: 0.400, blue: 0.400) // #666666
}
