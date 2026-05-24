import Foundation

enum ServiceStatus {
    case running
    case stopped
    case zombie    // Port offen, /health antwortet nicht (B031/B018)
    case starting
    case stopping
    case unknown

    var label: String {
        switch self {
        case .running:  return "RUNNING"
        case .stopped:  return "STOPPED"
        case .zombie:   return "ZOMBIE"
        case .starting: return "STARTING"
        case .stopping: return "STOPPING"
        case .unknown:  return "UNKNOWN"
        }
    }

    var color: AppColor {
        switch self {
        case .running:  return .green
        case .stopped:  return .red
        case .zombie:   return .orange
        case .starting: return .blue
        case .stopping: return .blue
        case .unknown:  return .gray
        }
    }
}

enum AppColor {
    case green, red, orange, blue, gray
}

struct Service: Identifiable {
    let id: String          // z.B. "jarvis-core"
    let displayName: String
    let port: Int?          // nil = kein HTTP-Port (speech_input, supervisor)
    let healthPath: String  // "/health"
    let launchAgentID: String  // "com.jarvis.v2.server"
    var status: ServiceStatus = .unknown
    var pid: Int?

    // Die 5 Jarvis-Services in Start-Reihenfolge
    static let all: [Service] = [
        Service(
            id: "jarvis-core",
            displayName: "jarvis-core",
            port: 8340,
            healthPath: "/health",
            launchAgentID: "com.jarvis.v2.server"
        ),
        Service(
            id: "jarvis-audio",
            displayName: "jarvis-audio",
            port: 8341,
            healthPath: "/health",
            launchAgentID: "com.jarvis.v2.audio"
        ),
        Service(
            id: "jarvis-ha",
            displayName: "jarvis-ha",
            port: 8342,
            healthPath: "/health",
            launchAgentID: "com.jarvis.v2.ha"
        ),
        Service(
            id: "speech-input",
            displayName: "speech_input",
            port: nil,
            healthPath: "",
            launchAgentID: "com.jarvis.v2.speech"
        ),
        Service(
            id: "supervisor",
            displayName: "supervisor",
            port: nil,
            healthPath: "",
            launchAgentID: "com.jarvis.v2.supervisor"
        ),
    ]
}
