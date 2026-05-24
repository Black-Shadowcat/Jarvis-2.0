import Foundation
import Network
import os

// Polls all Jarvis services every 5s.
// Port open + /health OK  -> .running
// Port open + /health fail -> .zombie  (I-2, I-5: TCP liegt nicht)
// Port closed              -> .stopped
@MainActor
class ServiceMonitor: ObservableObject {
    @Published var services: [Service] = Service.all
    @Published var autostartEnabled: Bool = false

    private var timer: Timer?
    private let session: URLSession = {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = 3
        cfg.timeoutIntervalForResource = 3
        return URLSession(configuration: cfg)
    }()

    func start() {
        checkAll()
        timer = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.checkAll() }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    func checkAll() {
        checkAutostart()
        for i in services.indices {
            let svc = services[i]
            Task { @MainActor in
                let status = await self.checkService(svc)
                self.services[i].status = status
            }
        }
    }

    // I-2: Port offen reicht nicht — /health muss antworten
    private func checkService(_ svc: Service) async -> ServiceStatus {
        guard let port = svc.port else {
            return await checkProcessRunning(svc.launchAgentID)
        }

        let portOpen = await isPortOpen(port)
        guard portOpen else { return .stopped }

        // Port ist offen — jetzt /health prüfen
        let healthy = await checkHealth(port: port, path: svc.healthPath)
        return healthy ? .running : .zombie  // I-6: zombie wenn Port offen aber health fail
    }

    private func isPortOpen(_ port: Int) async -> Bool {
        await withCheckedContinuation { continuation in
            let host = NWEndpoint.Host("127.0.0.1")
            let nwPort = NWEndpoint.Port(rawValue: UInt16(port))!
            let conn = NWConnection(host: host, port: nwPort, using: .tcp)
            // Nonisolated flag via OSAllocatedUnfairLock fuer Swift 6 Concurrency
            let resumed = OSAllocatedUnfairLock(initialState: false)

            conn.stateUpdateHandler = { state in
                let alreadyResumed = resumed.withLock { current -> Bool in
                    if current { return true }
                    return false
                }
                guard !alreadyResumed else { return }
                switch state {
                case .ready:
                    resumed.withLock { $0 = true }
                    conn.cancel()
                    continuation.resume(returning: true)
                case .failed, .cancelled:
                    resumed.withLock { $0 = true }
                    continuation.resume(returning: false)
                default:
                    break
                }
            }
            conn.start(queue: .global())

            // 2s Timeout
            DispatchQueue.global().asyncAfter(deadline: .now() + 2) {
                let alreadyResumed = resumed.withLock { current -> Bool in
                    if current { return true }
                    current = true
                    return false
                }
                guard !alreadyResumed else { return }
                conn.cancel()
                continuation.resume(returning: false)
            }
        }
    }

    private func checkHealth(port: Int, path: String) async -> Bool {
        guard let url = URL(string: "http://localhost:\(port)\(path)") else { return false }
        do {
            let (_, response) = try await session.data(from: url)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // Fuer Services ohne Port: pruefen ob LaunchAgent-Prozess laeuft
    private func checkProcessRunning(_ launchAgentID: String) async -> ServiceStatus {
        let result = await ShellExecutor.run("/bin/launchctl", args: ["list", launchAgentID])
        if result.exitCode == 0 {
            // PID aus Output lesen (erste Spalte der launchctl list Ausgabe)
            let pid = parsePIDFromLaunchctl(result.output)
            return pid > 0 ? .running : .stopped
        }
        return .stopped
    }

    private func parsePIDFromLaunchctl(_ output: String) -> Int {
        // launchctl list <label> gibt ein Dict: "PID" = 758;
        for line in output.components(separatedBy: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            guard trimmed.hasPrefix("\"PID\"") else { continue }
            // Format: "PID" = 758;
            let parts = trimmed.components(separatedBy: "=")
            guard parts.count >= 2 else { continue }
            let rawValue = parts[1].trimmingCharacters(in: .whitespaces)
                .replacingOccurrences(of: ";", with: "")
                .trimmingCharacters(in: .whitespaces)
            if let pid = Int(rawValue), pid > 0 { return pid }
        }
        return 0
    }

    // Autostart = alle LaunchAgents geladen?
    private func checkAutostart() {
        Task {
            let result = await ShellExecutor.run("/bin/launchctl", args: ["list"])
            let loaded = result.output.contains("com.jarvis.v2.server")
            await MainActor.run { self.autostartEnabled = loaded }
        }
    }
}
