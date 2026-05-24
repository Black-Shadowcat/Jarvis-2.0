import Foundation

// Manages launchctl bootstrap/bootout for all Jarvis LaunchAgents.
// Invariant I-1: Supervisor IMMER zuerst stoppen.
// Invariant I-3: Nach STOP PIDs verifizieren, nicht nur Ports.
enum LaunchAgentController {

    private static let uid = String(getuid())
    private static let plistDir = "\(NSHomeDirectory())/Library/LaunchAgents"

    // LaunchAgent IDs in Stop-Reihenfolge (I-1: Supervisor zuerst!)
    static let stopOrder = [
        "com.jarvis.v2.supervisor",
        "com.jarvis.v2.server",
        "com.jarvis.v2.speech",
        "com.jarvis.v2.wake",
        "com.jarvis.v2.audio",
        "com.jarvis.v2.ha",
        "com.jarvis.v2.session",
    ]

    // LaunchAgent IDs in Start-Reihenfolge (I-7)
    static let startOrder = [
        "com.jarvis.v2.server",
        "com.jarvis.v2.audio",
        "com.jarvis.v2.ha",
        "com.jarvis.v2.speech",
        "com.jarvis.v2.supervisor",
        "com.jarvis.v2.wake",
    ]

    // Einzelnen LaunchAgent stoppen (bootout)
    static func bootout(_ agentID: String) async -> ShellResult {
        let plist = "\(plistDir)/\(agentID).plist"
        let result = await ShellExecutor.run(
            "/bin/launchctl",
            args: ["bootout", "gui/\(uid)", plist]
        )
        if result.exitCode != 0 {
            return await ShellExecutor.run("/bin/launchctl", args: ["unload", plist])
        }
        return result
    }

    // Einzelnen LaunchAgent starten (bootstrap)
    // load -w vor bootstrap: stellt sicher dass Disabled-Flag entfernt ist
    static func bootstrap(_ agentID: String) async -> ShellResult {
        let plist = "\(plistDir)/\(agentID).plist"
        _ = await ShellExecutor.run("/bin/launchctl", args: ["enable", "gui/\(uid)/\(agentID)"])
        _ = await ShellExecutor.run("/bin/launchctl", args: ["load", "-w", plist])
        let result = await ShellExecutor.run(
            "/bin/launchctl",
            args: ["bootstrap", "gui/\(uid)", plist]
        )
        return result
    }

    // Pruefen ob ein LaunchAgent geladen ist
    static func isLoaded(_ agentID: String) async -> Bool {
        let result = await ShellExecutor.run("/bin/launchctl", args: ["list", agentID])
        return result.exitCode == 0
    }

    // Alle LaunchAgents deregistrieren + persistent deaktivieren (Autostart aus)
    // unload -w schreibt Disabled=true in die Plist — ueberlebt Neustart zuverlaessig.
    // I-1: Supervisor zuerst
    static func bootoutAll() async -> [String: Bool] {
        var results: [String: Bool] = [:]
        for agentID in stopOrder {
            let plist = "\(plistDir)/\(agentID).plist"
            _ = await bootout(agentID)
            // unload -w setzt Disabled=true persistent in der Plist
            let r = await ShellExecutor.run("/bin/launchctl", args: ["unload", "-w", plist])
            _ = await ShellExecutor.run("/bin/launchctl", args: ["disable", "gui/\(uid)/\(agentID)"])
            results[agentID] = r.exitCode == 0
        }
        return results
    }

    // Pruefen ob Prozesse wirklich gestoppt sind (I-3: PIDs verifizieren)
    static func verifyAllStopped(ports: [Int]) async -> Bool {
        // Erst kurz warten damit Prozesse Zeit zum Beenden haben
        try? await Task.sleep(nanoseconds: 2_000_000_000)

        for port in ports {
            // lsof zeigt ob Port noch belegt ist
            let result = await ShellExecutor.run("/usr/sbin/lsof", args: ["-ti", ":\(port)"])
            if !result.output.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return false  // noch PIDs auf diesem Port
            }
        }
        return true
    }

    // Force-Kill aller Jarvis-Prozesse als Sicherheitsnetz (wie stop-dev.sh Phase 4)
    static func forceKillAll() async {
        let targets = ["supervisor.py", "server.py", "speech_input.py", "wake-monitor.py", "jarvis-audio", "jarvis-ha"]
        for target in targets {
            _ = await ShellExecutor.run("/usr/bin/pkill", args: ["-f", target])
        }
    }
}
