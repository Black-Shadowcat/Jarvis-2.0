# J.A.R.V.I.S. 2.0 — Troubleshooting Guide

**Version:** 1.2.0  
**Letztes Update:** Mai 2026

---

## 🔍 Problemdiagnose

### **WebSocket/Verbindungsfehler**

**Problem:** Browser zeigt "Disconnected" (HUD rot)

**Ursachen & Lösungen:**
1. **Server nicht laufen?**
   ```bash
   # Check ob Server antwortet
   curl http://localhost:8340/
   # Falls nicht: neu starten
   python3.11 server.py
   ```

2. **Firewall blockiert lokal-Zugriff?**
   - Prüfe: System Preferences → Security & Privacy → Firewall
   - Lösung: `localhost:8340` zulassen oder Firewall temporär deaktivieren

3. **Browser-Cache Problem?**
   - Cmd+Shift+R (Force reload mit Cache clear)
   - Oder: DevTools → Application → Clear Storage

4. **WebSocket-Timeout (langes Warten)?**
   - Browser konsole öffnen (Cmd+Option+I)
   - Schau auf Network Tab: Gibt's Errors bei WebSocket?
   - Falls ja: Server neu starten

---

### **Spracherkennung funktioniert nicht**

**Problem:** Kein Audio-Input, oder "Jarvis" wird nicht erkannt

**Diagnose:**
```bash
# Check ob Mikrofon erkannt wird
python3.11 -c "import pyaudio; p = pyaudio.PyAudio(); print([d for d in range(p.get_device_count())])"
```

**Lösungen:**
1. **Mikrofon-Berechtigung in macOS?**
   - System Preferences → Security & Privacy → Microphone
   - Finde "Google Chrome" oder "Chromium" → Allow

2. **Falsches Mikrofon?**
   - In Chrome: chrome://settings/content/microphone
   - Oder: Audio-Input in Browser-Console testen

3. **Zu laute Umgebung?**
   - "Jarvis aktivieren" braucht ~70 dB Sprachpegel
   - Näher zum Mikrofon sprechen

4. **Sprache nicht erkannt?**
   - Ist `language: "de"` in config.json?
   - Falls `"en"`: Deutsche Wörter werden nicht erkannt
   - Wechsel zu korrekter Sprache in Settings (⚙️)

---

### **E-Mails zeigen sich nicht / sind veraltet**

**Problem:** Mail-Anzeige leer oder zeigt alte Nachrichten

**Diagnose:**
```bash
# Direkt Mail.app testen
osascript -e 'tell application "Mail" to get unread count'
```

**Lösungen:**
1. **Mail.app neu starten:**
   ```bash
   killall Mail
   sleep 2
   open -a Mail
   ```

2. **Jarvis neu starten:**
   ```bash
   # Beende Jarvis
   pkill -f "python3.11 server.py"
   # Warte 2 Sekunden
   sleep 2
   # Starte neu
   python3.11 server.py
   ```

3. **Cache forciert clearen:**
   - Lösche `data/daily_brief_memory.json`:
     ```bash
     rm ~/Jarvis-2.0/data/daily_brief_memory.json
     ```
   - Jarvis neu starten — neuer Cache wird erstellt

4. **Mail-Berechtigungen?**
   - System Preferences → Security & Privacy → Full Disk Access
   - Prüfe ob Terminal/Python dort ist

---

### **Tasks/Reminders aktualisieren nicht**

**Problem:** To-Do-Liste zeigt veraltete oder keine Einträge

**Lösungen:**
1. **Reminders.app neu starten:**
   ```bash
   killall Reminders
   sleep 2
   open -a Reminders
   ```

2. **Cache clearen:**
   ```bash
   rm ~/Jarvis-2.0/data/daily_brief_memory.json
   ```

3. **AppleScript testen:**
   ```bash
   osascript -e 'tell app "Reminders" to get name of every reminder whose completed is false'
   ```
   - Falls leer: Keine Reminders in der App vorhanden
   - Falls error: Berechtigungsproblem

---

### **Langsame Responses / Startup braucht >10s**

**Problem:** Jarvis brauch lange zum Starten oder antwortet langsam

**Diagnose:**
```bash
# Startup-Zeit messen
time python3.11 server.py
# (Dann Ctrl+C nach ~5 Sekunden)
```

**Lösungen (M16 Performance):**
1. **Parallel-Fetching nutzen?**
   - Seit M16: Mail/Tasks/Weather sollten parallel laufen
   - Falls noch slow: Siehe Performance-Logs

2. **Home Assistant timeout?**
   - Falls HA offline: -3 Sekunden Timeout
   - Solution: `ha_enabled: false` in config.json falls nicht nötig

3. **Disk voll?**
   ```bash
   # Check Disk-Space
   df -h /Users/$(whoami)
   # Falls <5GB: Aufräumen!
   ```

4. **Speicherleck?**
   ```bash
   # Monitor memory über Zeit
   ps aux | grep python | grep server.py
   # Wenn RSS wächst: Logbericht eröffnen
   ```

---

### **Memory/CPU-Auslastung zu hoch**

**Problem:** Jarvis braucht >500 MB RAM oder 100% CPU

**Diagnostik:**
```bash
# Monitor real-time
top -p $(pgrep -f "python3.11 server.py")
```

**Lösungen:**
1. **Logs rotieren?**
   - Logfiles sind auf 10 MB begrenzt (RotatingFileHandler)
   - Falls trotzdem groß: Manuell clearen:
     ```bash
     rm ~/Library/Logs/jarvis-v2/*.log*
     ```

2. **WebSocket-Connections accumulieren?**
   - Browser-Tab zu?
   - Falls mehrere Tabs: Alle außer einem schließen

3. **Background-Tasks laufen?**
   - News-System, Daily Brief, Health Monitor
   - Diese sind normal (aber sollten <50 MB sein)

---

### **Home Assistant Integration funktioniert nicht**

**Problem:** Lichter anschalten geht nicht, Calendar zeigt nichts

**Diagnose:**
```bash
# Test HA-Connection
curl -H "Authorization: Bearer YOUR_TOKEN" http://YOUR_HA_IP:8123/api/states/light.wohnzimmer
```

**Lösungen:**
1. **HA-URL richtig?**
   - Format: `http://192.168.1.100:8123` (nicht https, nicht mit `/api`)
   - Check in config.json: `ha_url`, `ha_token`

2. **Token ungültig?**
   - Home Assistant → Profile → Create Long-lived Access Token
   - Kopiere Token in `config.json`: `ha_token`

3. **Network-Verbindung?**
   ```bash
   ping <HA-IP>
   # Falls nicht antwortet: HA ist offline
   ```

4. **Graceful Degradation (M13)?**
   - Falls HA offline: Jarvis nutzt gecachte Daten
   - Das ist beabsichtigt! Kein Fehler.

---

## 📋 Log-Dateien

### Wo sind die Logs?

```bash
# Hauptserver-Logs
~/Library/Logs/jarvis-v2/server.log

# Microservice (HA, Audio)
~/Library/Logs/jarvis-v2/ha.log
~/Library/Logs/jarvis-v2/audio.log

# Browser Console
Chrome DevTools → Console (Cmd+Option+I)
```

### Logs lesen

```bash
# Letzten 50 Zeilen
tail -50 ~/Library/Logs/jarvis-v2/server.log

# Real-time monitoring
tail -f ~/Library/Logs/jarvis-v2/server.log

# Errors suchen
grep ERROR ~/Library/Logs/jarvis-v2/server.log
```

### Wichtige Log-Messages

| Message | Bedeutung | Aktion |
|---------|-----------|--------|
| `[mail] ETag match` | Daten nicht geändert (M14) | OK — normal |
| `[daily_brief] Pause detected` | Pause erkannt | OK — normal |
| `Calendar availability` | Busy-Status gecheckt (M15) | OK — normal |
| `WARNING: timeout` | Service zu langsam | Siehe Performance |
| `ERROR` | Fehler! | Troubleshoot oder report |

---

## 🔄 System-Neustart

### Schnell: Nur Jarvis neu starten
```bash
# Beende Jarvis
pkill -f "python3.11 server.py"
# Starte neu
python3.11 server.py
```

### Gründlich: Alle Services neu starten
```bash
# Stop all
launchctl stop com.jarvis.v2.supervisor
launchctl stop com.jarvis.v2.audio
sleep 2
# Start again
launchctl start com.jarvis.v2.supervisor
sleep 3
# Check
launchctl list | grep jarvis
```

### Komplett: Vom Scratch
```bash
# 1. Kill everything
pkill -f jarvis
pkill -f python3.11
# 2. Clear caches
rm ~/Jarvis-2.0/data/daily_brief_memory.json
# 3. Restart
cd ~/Jarvis-2.0
python3.11 server.py
```

---

## ✅ Gesundheits-Checkup

```bash
# Allgemeiner Health Check
curl http://localhost:8340/api/health | jq .

# Supervisor Status
curl http://localhost:8340/api/supervisor/status | jq .

# Jarvis-HA Service
curl http://localhost:8342/health | jq .

# Audio Service
curl http://localhost:8341/health | jq .
```

Alle sollten `"status": "healthy"` zeigen!

---

## 📞 Wenn alles fehlschlägt

1. **Logs sammeln:**
   ```bash
   tail -100 ~/Library/Logs/jarvis-v2/server.log > /tmp/jarvis_logs.txt
   ```

2. **System-Info:**
   ```bash
   system_profiler SPHardwareDataType > /tmp/system_info.txt
   ```

3. **Issue eröffnen:**
   - GitHub: https://github.com/Black-Shadowcat/Jarvis-2.0/issues
   - Title: "Issue: [Dein Problem]"
   - Include: Logs + System-Info + Schritte zum Reproduzieren

---

**Version 1.2.0 — Viel Erfolg bei der Troubleshooting! 🛠️**
