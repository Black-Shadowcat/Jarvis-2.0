# Jarvis Manager

Native macOS Control App für das Jarvis 2.0 KI-Assistenten-System.

---

## Warum diese App?

Das Jarvis-Dashboard läuft unter `localhost:8340` — und ist damit **nur erreichbar, wenn der Server selbst läuft**. Bei einem Absturz, einem blockierten Port oder einer Endlosschleife ist das Dashboard nicht mehr nutzbar.

Der Jarvis Manager ist eine **serverunabhängige Notfall-Steuerung**: Er läuft als native SwiftUI-App direkt auf macOS, ohne jede Abhängigkeit vom Jarvis-Stack. Wenn Jarvis hängt, kann der Manager trotzdem starten, stoppen und den Status aller Services anzeigen.

---

## Was die App macht

- **Status aller 5 Jarvis-Services** in Echtzeit (5s Polling)
- **START** — startet alle Services in der richtigen Reihenfolge, wartet auf Health-Checks
- **STOP** — stoppt alle Services sauber (Supervisor zuerst, I-1)
- **RESTART** — Stop + Start mit Pause dazwischen
- **Zombie-Detection** — Port offen aber `/health` antwortet nicht → ZOMBIE-Warnung
- **Autostart deaktivieren** — entfernt LaunchAgents persistent, Jarvis startet nach Neustart nicht mehr automatisch

---

## Installation (Drag & Drop)

1. [`JarvisManager.zip`](JarvisManager.zip) herunterladen und entzippen
2. `Jarvis Manager.app` nach `~/Applications` ziehen
3. Beim ersten Start: **Rechtsklick → Öffnen** (einmalige Gatekeeper-Warnung)

> Kein Xcode, kein Build-Prozess nötig.

---

## Services & Status-Logik

| Service | Port | Erkennung |
|---|---|---|
| jarvis-core | 8340 | TCP + `/health` |
| jarvis-audio | 8341 | TCP + `/health` |
| jarvis-ha | 8342 | TCP + `/health` |
| speech-input | — | `launchctl` PID-Check |
| supervisor | — | `launchctl` PID-Check |

```
Port geschlossen            → STOPPED
Port offen + /health OK     → RUNNING
Port offen + /health fail   → ZOMBIE
launchctl PID > 0           → RUNNING
```

---

## Technisches

| Komponente | Detail |
|---|---|
| Framework | SwiftUI (macOS 13+) |
| Port-Check | NWConnection (Network.framework) |
| Health-Check | URLSession, 3s Timeout |
| Shell-Ausführung | Process() + Pipe (Live-Output) |
| LaunchAgent-Control | `launchctl bootstrap/bootout/unload -w/disable` |
| Concurrency | Swift 6, `@MainActor`, `OSAllocatedUnfairLock` |
| App Sandbox | **AUS** — erforderlich für Process() und launchctl |

### Warum nicht Tauri?

Die Jarvis-App (`Jarvis.app`) basiert auf Tauri. Wenn Tauri oder der Node-Prozess hängt, wäre auch ein Tauri-basierter Manager nicht nutzbar — gleicher Zirkelschluss. SwiftUI hat **keine Abhängigkeit** zum Jarvis-Stack.

---

## Selbst bauen

```bash
cd jarvis-manager

# Xcode-Projekt generieren (nach project.yml Änderungen)
xcodegen generate

# Build
xcodebuild -project JarvisManager.xcodeproj \
  -scheme JarvisManager \
  -configuration Release \
  -derivedDataPath build \
  clean build

# Deploy
cp -R "build/Build/Products/Release/Jarvis Manager.app" ~/Applications/
```

**Voraussetzung:** Xcode 16+ und [`xcodegen`](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`)
