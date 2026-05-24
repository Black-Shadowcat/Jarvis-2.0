import SwiftUI

struct ContentView: View {
    @StateObject private var monitor = ServiceMonitor()
    @State private var logEntries: [LogEntry] = []
    @State private var isWorking = false         // blockiert Buttons waehrend Aktion laeuft
    @State private var disableAutostart = false  // Checkbox "Autostart deaktivieren"
    @State private var showJarvisButton = false  // nach erfolgreichem START

    private let scriptDir = "\(NSHomeDirectory())/Jarvis-2.0/scripts"

    var body: some View {
        VStack(spacing: 0) {
            headerView
            Divider().background(HUDColor.panelBorder)
            serviceListView
            Divider().background(HUDColor.panelBorder)
            actionView
            Divider().background(HUDColor.panelBorder)
            logAreaView
        }
        .frame(width: 480, height: 580)
        .background(
            LinearGradient(
                colors: [HUDColor.background, HUDColor.backgroundAlt],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .onAppear { monitor.start() }
        .onDisappear { monitor.stop() }
    }

    // ── Header ───────────────────────────────��──────────────────────────────
    private var headerView: some View {
        HStack {
            Text("JARVIS MANAGER")
                .font(.custom("Courier New", size: 16))
                .fontWeight(.bold)
                .foregroundColor(HUDColor.green)
                .tracking(2)

            Spacer()

            // Gesamtstatus
            HStack(spacing: 6) {
                Circle()
                    .fill(overallStatusColor)
                    .frame(width: 8, height: 8)
                    .shadow(color: overallStatusColor.opacity(0.8), radius: 4)
                Text(overallStatusLabel)
                    .font(.custom("Courier New", size: 11))
                    .foregroundColor(overallStatusColor)
                    .tracking(1)
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 14)
        .background(HUDColor.background.opacity(0.8))
    }

    // ── Service-Liste ────────────────────────────────────────────────────────
    private var serviceListView: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(monitor.services) { svc in
                ServiceRowView(service: svc)
            }

            Divider()
                .background(HUDColor.panelBorder)
                .padding(.vertical, 4)

            HStack(spacing: 8) {
                Circle()
                    .fill(monitor.autostartEnabled ? HUDColor.green : HUDColor.gray)
                    .frame(width: 6, height: 6)
                Text("Autostart beim Login:")
                    .font(.custom("Courier New", size: 11))
                    .foregroundColor(HUDColor.textDim)
                Text(monitor.autostartEnabled ? "AN" : "AUS")
                    .font(.custom("Courier New", size: 11))
                    .fontWeight(.bold)
                    .foregroundColor(monitor.autostartEnabled ? HUDColor.green : HUDColor.gray)
            }
            .padding(.horizontal, 12)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 12)
    }

    // ── Aktions-Buttons ────────────────────────────────────────────���─────────
    private var actionView: some View {
        VStack(spacing: 10) {
            HStack(spacing: 12) {
                ActionButton(label: "START", color: HUDColor.green, disabled: isWorking) {
                    Task { await doStart() }
                }
                ActionButton(label: "STOP", color: HUDColor.red, disabled: isWorking) {
                    Task { await doStop() }
                }
                ActionButton(label: "RESTART", color: HUDColor.blue, disabled: isWorking) {
                    Task { await doRestart() }
                }
            }

            HStack(spacing: 8) {
                Toggle("", isOn: $disableAutostart)
                    .toggleStyle(CheckboxToggleStyle())
                    .labelsHidden()
                Text("Autostart deaktivieren beim Stoppen")
                    .font(.custom("Courier New", size: 11))
                    .foregroundColor(HUDColor.textDim)
                Spacer()

                // Optionaler "Jarvis oeffnen"-Button nach erfolgreichem START
                if showJarvisButton {
                    Button("JARVIS OEFFNEN") {
                        NSWorkspace.shared.openApplication(
                            at: URL(fileURLWithPath: "\(NSHomeDirectory())/Applications/Jarvis.app"),
                            configuration: .init()
                        )
                    }
                    .font(.custom("Courier New", size: 10))
                    .foregroundColor(HUDColor.green)
                    .buttonStyle(.plain)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .overlay(
                        RoundedRectangle(cornerRadius: 2)
                            .stroke(HUDColor.green.opacity(0.4), lineWidth: 1)
                    )
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
    }

    // ── Log-Bereich ───────────────────────��──────────────────────────���───────
    private var logAreaView: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("LOG")
                    .font(.custom("Courier New", size: 10))
                    .fontWeight(.bold)
                    .foregroundColor(HUDColor.green)
                    .tracking(2)
                Spacer()
                Button("LEEREN") {
                    logEntries.removeAll()
                }
                .font(.custom("Courier New", size: 9))
                .foregroundColor(HUDColor.textMuted)
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.top, 8)

            LogView(entries: logEntries)
        }
        .frame(maxHeight: 160)
    }

    // ── Gesamtstatus ─────��─────────────────────────��────────────────────────
    private var overallStatusColor: Color {
        let statuses = monitor.services.map(\.status)
        if statuses.contains(.zombie)            { return HUDColor.orange }
        if statuses.allSatisfy({ $0 == .running }) { return HUDColor.green }
        if statuses.allSatisfy({ $0 == .stopped }) { return HUDColor.red }
        return HUDColor.orange
    }

    private var overallStatusLabel: String {
        let statuses = monitor.services.map(\.status)
        if statuses.contains(.zombie)              { return "ZOMBIE DETECTED" }
        if statuses.allSatisfy({ $0 == .running }) { return "ALL RUNNING" }
        if statuses.allSatisfy({ $0 == .stopped }) { return "ALL STOPPED" }
        if statuses.contains(.starting)            { return "STARTING..." }
        if statuses.contains(.stopping)            { return "STOPPING..." }
        return "DEGRADED"
    }

    // ── Aktionen ──────────────────────���──────────────────────────────────────

    private func doStart() async {
        isWorking = true
        showJarvisButton = false
        log(.info, "START gestartet...")

        // I-6: Zombie-Check vor START
        await checkForZombies()

        // start-dev.sh aufrufen mit Live-Output
        let script = "\(scriptDir)/start-dev.sh"
        await runScript(script, successMessage: "System gestartet")

        // I-2: Warten bis /health auf allen 3 Ports antwortet (max 30s)
        log(.info, "Warte auf /health aller Services...")
        let ready = await waitForHealth(ports: [8340, 8341, 8342], timeout: 30)

        if ready {
            log(.ok, "System bereit — alle Services antworten")
            showJarvisButton = true
        } else {
            log(.warn, "Timeout: nicht alle Services meldeten sich innerhalb 30s")
        }

        monitor.checkAll()
        isWorking = false
    }

    private func doStop() async {
        isWorking = true
        showJarvisButton = false
        log(.info, "STOP gestartet...")

        let script = "\(scriptDir)/stop-dev.sh"
        await runScript(script, successMessage: "Stop-Script abgeschlossen")

        // Autostart deaktivieren wenn Checkbox gesetzt
        if disableAutostart {
            log(.info, "Deaktiviere Autostart (bootout aller LaunchAgents)...")
            let results = await LaunchAgentController.bootoutAll()
            let failed = results.filter { !$0.value }.keys
            if failed.isEmpty {
                log(.ok, "Autostart deaktiviert")
            } else {
                log(.warn, "Bootout fehlgeschlagen fuer: \(failed.joined(separator: ", "))")
            }
        }

        // I-3: Ports UND PIDs verifizieren
        log(.info, "Verifiziere dass alle Ports frei sind...")
        let stopped = await waitForPortsFree(ports: [8340, 8341, 8342], timeout: 15)

        if stopped {
            log(.ok, "Alle Ports frei — System gestoppt")
        } else {
            log(.warn, "Ports noch belegt — Force-Kill wird ausgefuehrt...")
            await LaunchAgentController.forceKillAll()
            log(.ok, "Force-Kill abgeschlossen")
        }

        monitor.checkAll()
        isWorking = false
    }

    private func doRestart() async {
        log(.info, "RESTART: Stoppe zuerst...")
        await doStop()
        // I-4: Kurze Pause zwischen STOP und START (B021)
        log(.info, "Pause 3s vor START...")
        try? await Task.sleep(nanoseconds: 3_000_000_000)
        log(.info, "RESTART: Starte jetzt...")
        await doStart()
    }

    // ── Hilfsmethoden ────────��───────────────────────────────────────────────

    private func runScript(_ path: String, successMessage: String) async {
        await withCheckedContinuation { continuation in
            ShellExecutor.runStreaming(
                script: path,
                onLine: { [self] line in
                    Task { @MainActor in self.log(.info, line) }
                },
                onDone: { [self] exitCode in
                    Task { @MainActor in
                        if exitCode == 0 {
                            self.log(.ok, successMessage)
                        } else {
                            self.log(.error, "Script beendet mit Code \(exitCode)")
                        }
                        continuation.resume()
                    }
                }
            )
        }
    }

    // I-6: Zombie-Check — Port offen aber /health antwortet nicht
    private func checkForZombies() async {
        for svc in monitor.services {
            if svc.status == .zombie {
                log(.warn, "ZOMBIE erkannt: \(svc.displayName) — Port belegt, Service antwortet nicht")
                log(.info, "Bereinige Zombie-Prozesse vor START...")
                await LaunchAgentController.forceKillAll()
                try? await Task.sleep(nanoseconds: 2_000_000_000)
                log(.ok, "Zombies bereinigt")
                return
            }
        }
    }

    // Warten bis alle /health-Endpoints antworten (I-2)
    private func waitForHealth(ports: [Int], timeout: TimeInterval) async -> Bool {
        let deadline = Date.now.addingTimeInterval(timeout)
        let session = URLSession(configuration: {
            let c = URLSessionConfiguration.ephemeral
            c.timeoutIntervalForRequest = 2
            return c
        }())

        while Date.now < deadline {
            var allHealthy = true
            for port in ports {
                guard let url = URL(string: "http://localhost:\(port)/health") else { continue }
                do {
                    let (_, resp) = try await session.data(from: url)
                    if (resp as? HTTPURLResponse)?.statusCode != 200 {
                        allHealthy = false
                    }
                } catch {
                    allHealthy = false
                }
            }
            if allHealthy { return true }
            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }
        return false
    }

    // Warten bis alle Ports frei sind (I-3)
    private func waitForPortsFree(ports: [Int], timeout: TimeInterval) async -> Bool {
        let deadline = Date.now.addingTimeInterval(timeout)
        while Date.now < deadline {
            let allFree = await LaunchAgentController.verifyAllStopped(ports: ports)
            if allFree { return true }
            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }
        return false
    }

    private func log(_ level: LogLevel, _ message: String) {
        logEntries.append(LogEntry(timestamp: .now, message: message, level: level))
        // Max 200 Eintraege im Log
        if logEntries.count > 200 {
            logEntries.removeFirst(logEntries.count - 200)
        }
    }
}

// ── Hilfs-Views ────────────────���─────────────────────────────────────────────

struct ActionButton: View {
    let label: String
    let color: Color
    let disabled: Bool
    let action: () -> Void

    var body: some View {
        Button(label) { action() }
            .font(.custom("Courier New", size: 12))
            .fontWeight(.bold)
            .foregroundColor(disabled ? color.opacity(0.3) : color)
            .tracking(1)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .frame(maxWidth: .infinity)
            .overlay(
                RoundedRectangle(cornerRadius: 2)
                    .stroke(disabled ? color.opacity(0.1) : color.opacity(0.4), lineWidth: 1)
            )
            .background(
                RoundedRectangle(cornerRadius: 2)
                    .fill(color.opacity(disabled ? 0.02 : 0.05))
            )
            .disabled(disabled)
            .buttonStyle(.plain)
    }
}
