# J.A.R.V.I.S. 2.0 — Benutzerhandbuch

**Version:** 1.2.0  
**Datum:** Mai 2026  
**Sprache:** Deutsch & English

---

## 🤖 Was ist Jarvis?

**Jarvis** ist ein persönlicher KI-Assistent mit Sprachsteuerung für macOS. Sie sprechen, Jarvis hört zu, denkt mit Claude AI und antwortet — alles lokal, datenschutzkonform, ohne Cloud-Grenzen.

### Hauptfunktionen
- 🎤 **Sprachsteuerung** — Befehle per Stimme geben
- 📧 **E-Mail Zugriff** — Ungelesene E-Mails abrufen
- ✅ **Aufgaben & Erinnerungen** — To-Do-Liste & Kalender
- 🌤️ **Wettervorhersage** — Aktuelle Wetterdaten
- 💡 **Smart Home** — Lichter steuern (Home Assistant)
- 📝 **Notizen** — Obsidian-Integration
- 🧠 **Intelligente Briefe** — Morgen-, Pause-, Abend-Zusammenfassungen

---

## 🚀 Erste Schritte

### 1. Installation
```bash
cd ~/Jarvis-2.0
pip install -r requirements.txt
playwright install chromium
python3.11 server.py
```

### 2. Konfiguration
Bearbeite `config.json`:
```json
{
  "user_name": "Dein Name",
  "user_address": "Deine bevorzugte Anrede",
  "language": "de",
  "city": "Deine Stadt",
  "anthropic_api_key": "DEIN_API_KEY"
}
```

### 3. Starten
- **Mac-Hotkey:** `Cmd+Shift+J` (startet Jarvis + Browser)
- **Oder manuell:** `python3.11 server.py` in Terminal
- **Dann:** Browser öffnet sich automatisch auf `http://localhost:8340`

---

## 🎤 Sprachbefehle

### "Jarvis, aktiviere mich!"
Startet eine Spracheingabe. Sagen Sie danach einen Befehl:

#### E-Mails
- "Zeige meine ungelesenen E-Mails"
- "Ich habe neue Nachrichten?"

#### Aufgaben
- "Was steht auf meiner To-Do-Liste?"
- "Zeige meine Erinnerungen"

#### Wetter
- "Wie ist das Wetter heute?"
- "Regnet es morgen?"

#### Lichter (Home Assistant)
- "Mach das Licht an" (alle Lichter)
- "Schalte die Küchenstrahler aus"
- "Stelle das Wohnzimmer auf 50 Prozent"

#### Notizen
- "Zeige meine ausstehenden Notizen"
- "Erstelle eine neue Notiz: Einkaufen"

#### Allgemein
- "Welche Zeit ist es?"
- "Öffne Google"
- "Spiele meine Musik"
- "Aktiviere meinen Timer"

---

## 📊 Dashboard Übersicht

### Linke Seitenleiste
- **HUD:** Status (online, idle, aktiv)
- **Health:** Dienststatus (grün = OK, rot = Problem)
- **Logs:** Letzte Aktivitäten

### Hauptbereich
- **Ungelesene E-Mails:** Absender + Betreffzeile
- **Aufgaben:** To-Do-Liste aus Reminders.app
- **Wetter:** Aktuelle + Vorhersage
- **Kalender:** Heutige Termine

### Rechte Bedienelemente
- **Sprache:** Switch zwischen DE/EN
- **Einstellungen:** Gear-Icon für Konfiguration
- **Handbuch:** Help-Icon für Anleitung

---

## ⚙️ Einstellungen & Anpassung

### In der Web-UI
Klick auf ⚙️ (Settings) für:
- 👤 **Benutzer-Name** — Wie soll Jarvis Sie nennen?
- 🗣️ **Sprache** — Deutsch oder English
- 📍 **Stadt & Koordinaten** — Für Wetter
- 🏠 **Home Assistant URL** — Für Smart Home
- 📝 **Obsidian Inbox** — Für Notizen-Sync

### In der config.json
Bearbeite `/Jarvis-2.0/config.json` für erweiterte Einstellungen:
```json
{
  "language": "de",
  "ha_enabled": true,
  "ha_url": "http://192.168.1.100:8123",
  "kachelmann_api_key": "IHR_API_KEY"
}
```

---

## 📈 Intelligente Briefe (M15)

Jarvis gibt Ihnen automatisch Zusammenfassungen:

### 🌅 Morgen-Brief (ab 6 Uhr)
- Tagesübersicht
- Wetterwarnung + Schirmempfehlung
- Neue E-Mails & Aufgaben

### ⏸️ Pause-Return (nach 30 Min inaktiv)
- "Willkommen zurück!"
- Neue E-Mails seit der Pause
- Status der Aufgaben

### 🌙 Abend-Brief (nach 17 Uhr)
- Tagesabschluss
- Offene Aufgaben für morgen

**Anpassung:** Thresholds in `data/daily_brief_memory.json`
```json
{
  "pause_threshold_minutes": 30,
  "long_absence_threshold_minutes": 90
}
```

---

## 🔋 Performance & Optimierungen

### Startup-Zeit
- Ideal: ~3-4 Sekunden
- Falls länger: Siehe **Troubleshooting**

### Response-Zeit
- Spracherkennung: <1s
- E-Mail laden: <3s (mit M14 ETag-Caching)
- Lichter steuern: <1s

### Speichernutzung
- Startup: ~150 MB
- Steady-state: ~200-250 MB
- Nach 8h: Sollte stabil bleiben (kein Leak)

---

## ❓ FAQ

### **F: Funktioniert Jarvis ohne Internet?**
Ja! Lokale Spracherkennung (mlx-whisper) + lokale KI (Claude lokal lädt nicht, aber API) = teil-offline möglich. E-Mail, Wetter, Smart Home brauchen aber Netzwerk.

### **F: Ist meine Sprachein- und -ausgabe privat?**
Ja! Alles läuft lokal. Nur die Claude API-Anfrage geht an Anthropic (verschlüsselt).

### **F: Kann ich Jarvis ohne macOS nutzen?**
Aktuell: Nur macOS (nutzt macOS-APIs). Linux-Version ist geplant.

### **F: Warum reagiert Jarvis manchmal nicht?**
Häufige Gründe:
1. WebSocket-Verbindung unterbrochen → Browser neu laden
2. Home Assistant offline → Fallback zu gecachten Daten (M13)
3. Mikrofon blockiert (Browser-Berechtigung) → Settings checken

### **F: Wie viele Anfragen pro Minute?**
~1-2 API-Anfragen pro Sprachbefehl. Mit M14 ETag-Caching sinkt dies auf <1/Minute.

### **F: Kann ich Jarvis erweitern?**
Ja! Siehe **Developer Guide** für:
- Custom voice commands hinzufügen
- Home Assistant-Integration erweitern
- Neue Datenquellen anbinden

### **F: Wo finde ich Support?**
- GitHub: https://github.com/Black-Shadowcat/Jarvis-2.0/issues
- Dokumentation: Siehe `/Jarvis-2.0/README.md` & dieses Handbuch
- Troubleshooting: Nächster Abschnitt!

---

## 🆘 Schnelle Problembehebung

| Problem | Schnelllösung |
|---------|--------------|
| **Jarvis antwortet nicht** | Browser neu laden (Cmd+R) |
| **Mikrofon funktioniert nicht** | Lautstärke checken, Browser-Berechtigung prüfen |
| **E-Mails zeigen sich nicht** | Mail.app neustarten, Jarvis neu starten |
| **Langsam beim Start** | Siehe Troubleshooting Guide |
| **Home Assistant integriert nicht** | HA URL & Token in config.json prüfen |

**Detaillierte Lösungen:** Siehe `JARVIS_TROUBLESHOOTING.md`

---

## 📞 Kontakt & Feedback

- **GitHub Issues:** https://github.com/Black-Shadowcat/Jarvis-2.0/issues
- **E-Mail:** schreiber1970@gmail.com
- **Feature-Requests:** Wilkommen! Issue eröffnen oder mitcodieren.

---

**Version 1.2.0 — Happy Assisting! 🚀**
