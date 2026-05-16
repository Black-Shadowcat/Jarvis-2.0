# Mikrofon-Konfiguration für Jarvis 2.0

> Anleitung zum Wechsel auf ein neues Mikrofon und Kalibrierung der VAD-Schwellwerte

---

## Übersicht

Jarvis verwendet **Voice Activity Detection (VAD)** mit RMS-Schwellwerten zur Wake-Word-Erkennung:
- `WW_VOICE_RMS` — ab welchem RMS wird Sprache erkannt?
- `WW_SILENCE_RMS` — unter welchem RMS ist es Stille?

Diese Werte sind **Mikrofon-spezifisch**! Verschiedene Mikrofone liefern unterschiedliche RMS-Werte.

---

## Schritt 1: Mikrofon in macOS auswählen

```bash
# Verfügbare Audiogeräte anzeigen
system_profiler SPAudioDataType

# oder Terminal → Systemeinstellungen → Ton → Eingabe
```

Stelle sicher, dass dein externes Mikrofon als **Standard-Eingabegerät** ausgewählt ist.

---

## Schritt 2: Input-Lautstärke anpassen

Die macOS Input-Lautstärke beeinflusst die RMS-Werte erheblich:

```bash
# Aktuelle Lautstärke anzeigen
osascript -e "output volume of (get volume settings)"

# Auf 75% setzen
osascript -e "set volume input volume 75"

# Auf 85% setzen
osascript -e "set volume input volume 85"
```

**Faustregel:** Externe Mikrofone brauchen oft niedrigere Lautstärke (70-80%) als Monitor-Mikrofone.

---

## Schritt 3: VAD-Schwellwerte kalibrieren

### Automatische Kalibrierung (empfohlen)

```bash
cd ~/Jarvis-2.0
python3.11 scripts/calibrate-vad.py
```

Das Skript:
1. Misst 3 Sekunden **Stille** (ohne Geräusche)
2. Misst 5 Sekunden **Sprache** (normales Sprechen)
3. Empfiehlt neue RMS-Werte basierend auf den Messungen

**Output-Beispiel:**
```
📌 Stille:
   WW_SILENCE_RMS = 0.0025  (max silence + 20% margin)

📌 Sprache:
   WW_VOICE_RMS = 0.0085  (min speech - 20% margin)
```

### Manuelle Kalibrierung (falls nötig)

Falls die automatische Kalibrierung nicht funktioniert:

```bash
# 1. Speech-Input starten
cd ~/Jarvis-2.0
python3.11 speech_input.py

# 2. In anderer Konsole: RMS-Werte beobachten
tail -f ~/Library/Logs/jarvis-v2/speech.log | grep RMS
```

Dann spreche verschiedene Sätze und beobachte die RMS-Werte im Log.

---

## Schritt 4: Werte in Code aktualisieren

```bash
nano ~/Jarvis-2.0/speech_input.py
```

**Zeilen 50-51 anpassen:**

```python
WW_VOICE_RMS    = 0.0085   # (statt 0.012)
WW_SILENCE_RMS  = 0.0025   # (statt 0.008)
```

---

## Schritt 5: Service neu starten

```bash
launchctl kickstart -k gui/501/com.jarvis.v2.speech

# Verifiziere dass der Service läuft
ps aux | grep speech_input
```

---

## Schritt 6: Testen

```bash
# 1. Sag "Jarvis" − sollte erkannt werden
# 2. Warte auf Bestätigung
# 3. Sprich deinen Befehl

# Wenn es nicht funktioniert:
tail -f ~/Library/Logs/jarvis-v2/speech.log | grep "WW-Snippet\|Wake-Word"
```

---

## Troubleshooting

| Problem | Lösung |
|---------|--------|
| Wake-Word wird **nicht** erkannt | `WW_VOICE_RMS` zu hoch → Wert senken (z.B. 0.008 statt 0.012) |
| Wake-Word wird **zu oft** erkannt (Fehlalarme) | `WW_VOICE_RMS` zu niedrig → Wert erhöhen |
| Auto-Listen stoppt zu früh | `WW_SILENCE_RMS` zu hoch → Wert senken |
| Audio/Rauschen triggert Wake-Word | `WW_SILENCE_RMS` zu niedrig → Wert erhöhen, oder Input-Lautstärke senken |

---

## Referenz: Alte vs. Neue Werte

| Komponente | MateView Monitor | Externes Mikrofon (Beispiel) |
|---|---|---|
| Gerät | MateView Monitor | [dein Mikrofon] |
| Input-Lautstärke | 82% | 70-80% (testen!) |
| `WW_VOICE_RMS` | 0.012 | 0.0085–0.015 |
| `WW_SILENCE_RMS` | 0.008 | 0.002–0.005 |

---

## Weitere Anpassungen

### WW_MAX_SECS (max Snippet-Länge)

Falls Wake-Word-Erkennung abbricht:

```python
WW_MAX_SECS = 5.0  # Standard (5 Sekunden für Wake-Word-Snippet)
```

Auf 7.0 erhöhen, wenn schnelle Sprecher nicht erkannt werden.

### WW_SILENCE_SECS (Stille nach Wort → Ende)

```python
WW_SILENCE_SECS = 0.8  # Standard (0.8 Sekunden Stille → fertig)
```

Erhöhen (z.B. 1.0), wenn Zwischen-Pausen fälschlicherweise das Snippet beenden.

### WW_CMD_SILENCE (Stille nach Befehl → Stop)

```python
WW_CMD_SILENCE = 1.5  # Standard (1.5 Sekunden Stille → Aufnahme beenden)
```

---

## Dokumentation aktualisieren

Wenn die Kalibrierung fertig ist, aktualisiere `CURRENT_STATE.md`:

```markdown
## Mikrofon-Konfiguration

| Eigenschaft | Wert |
|---|---|
| Gerät | [dein Mikrofon] |
| macOS Input-Lautstärke | XX% |
| `WW_VOICE_RMS` | `0.0085` |
| `WW_SILENCE_RMS` | `0.0025` |
| `WW_MAX_SECS` | `5.0` |
| `WW_SILENCE_SECS` | `0.8` |
```

---

## Tipps für beste Ergebnisse

1. **Stille-Umgebung:** Kalibriere in einer ruhigen Umgebung
2. **Konsistente Lautstärke:** Spreche während Kalibrierung mit normaler Lautstärke
3. **Mehrfach testen:** Kalibriere mehrmals und nimm die Durchschnittswerte
4. **Dokumentieren:** Notiere die Werte für zukünftige Referenz
5. **Regelmäßig testen:** Neue Umgebungen können neue Kalibrierung erfordern
