import Foundation

enum LogLevel {
    case ok, warn, error, info

    var prefix: String {
        switch self {
        case .ok:    return "OK"
        case .warn:  return "WARN"
        case .error: return "ERR"
        case .info:  return "INFO"
        }
    }
}

struct LogEntry: Identifiable {
    let id = UUID()
    let timestamp: Date
    let message: String
    let level: LogLevel

    var timeString: String {
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f.string(from: timestamp)
    }

    static func ok(_ msg: String)    -> LogEntry { LogEntry(timestamp: .now, message: msg, level: .ok) }
    static func warn(_ msg: String)  -> LogEntry { LogEntry(timestamp: .now, message: msg, level: .warn) }
    static func error(_ msg: String) -> LogEntry { LogEntry(timestamp: .now, message: msg, level: .error) }
    static func info(_ msg: String)  -> LogEntry { LogEntry(timestamp: .now, message: msg, level: .info) }
}
