# JARVIS Handbuch — Architektur & Wartung

## Übersicht

Das JARVIS-Handbuch ist ein mehrsprachiges, statisches HTML-System mit animiertem Cover-Page und sprachabhängigen Inhaltsseiten. Es wird über drei FastAPI-Routen bereitgestellt und benötigt keine externen Abhängigkeiten (alle Bilder sind als Base64 eingebunden).

**Kernidee:** Eine zentrale Cover-Seite (`/handbuch`) leitet Nutzer zu sprachspezifischen Handbüchern weiter (`/handbuch-de`, `/handbuch-en`). Jede Sprache hat ihre eigene HTML-Datei mit vollständiger Navigation und Inhalten.

---

## Dateistruktur

```
frontend/
├── handbuch-cover.html      # Cover-Seite mit animiertem HUD + Sprachwahlbuttons
├── handbuch.html            # Deutsches Handbuch (Vollständig)
├── handbuch-en.html         # Englisches Handbuch (Vollständig)
└── i18n/
    ├── de.json              # UI-Label (Deutsch)
    └── en.json              # UI-Label (Englisch)

server.py
# Drei Routen:
# GET /handbuch        → handbuch-cover.html
# GET /handbuch-de     → handbuch.html
# GET /handbuch-en     → handbuch-en.html
```

---

## Routen & Flow

### `/handbuch` — Cover Page
- **Datei:** `frontend/handbuch-cover.html`
- **Größe:** ~240 Zeilen
- **Inhalt:**
  - Animiertes HUD mit drei rotierenden Ringen (SVG, kein PNG-Import)
  - Tech-Specs Tabelle
  - Sprachwahlbuttons: 🇩🇪 Deutsch → `/handbuch-de` | 🇬🇧 English → `/handbuch-en`
- **Design:** Dark theme, grüne Akzente (#4cbf7e), responsive

### `/handbuch-de` — German Handbook
- **Datei:** `frontend/handbuch.html`
- **Größe:** ~1.3 MB
- **Inhalt:**
  - Sidebar mit ~25 Navigationslinks (5 Kategorien)
  - 20 Kapitel: Installation, Bedienung, System, Architektur, Referenz
  - 4 eingebettete Screenshots (Base64):
    - Jarvis-Icon (162 KB)
    - HUD-Screenshot (794 KB)
    - Config-UI Screenshot (434 KB)
    - Health Monitor Screenshot (458 KB)
  - Vollständige deutsche Dokumentation
- **Layout:** Fixed Sidebar (260px) + Scrollable Hauptinhalt

### `/handbuch-en` — English Handbook
- **Datei:** `frontend/handbuch-en.html`
- **Größe:** ~1.3 MB (identisch zu Deutsch)
- **Inhalt:** Komplette englische Übersetzung von `handbuch.html`
- **Layout:** Identisch zu deutschem Handbuch
- **Screenshots:** Identisch zu deutschem Handbuch (sprachunabhängig)

---

## Design-Komponenten

### 1. Cover-Page HUD Animation
**Datei:** `handbuch-cover.html` (Zeilen 70–140)

```html
<svg viewBox="0 0 300 300" class="hud-svg">
  <circle class="hud-ring hud-ring-1" cx="150" cy="150" r="120" />
  <circle class="hud-ring hud-ring-2" cx="150" cy="150" r="90" />
  <circle class="hud-ring hud-ring-3" cx="150" cy="150" r="60" />
  <circle cx="150" cy="150" r="30" fill="#1a1a1a" />
  <text x="150" y="160" text-anchor="middle" class="hud-text">J.A.R.V.I.S.</text>
</svg>
```

**CSS Animationen:**
- `.hud-ring-1`: Rotiert gegen den Uhrzeigersinn (CCW), 20s
- `.hud-ring-2`: Rotiert im Uhrzeigersinn (CW), 15s
- `.hud-ring-3`: Rotiert im Uhrzeigersinn (CW), 10s

**Ursprung:** Extrahiert aus `frontend/index.html` (Anwender-Feedback: Konsistentes Design verwenden)

### 2. Screenshot-Einbettung (Base64)
**Verwendete Screenshots:**
- `docs/jarvis-icon.png` → Icon auf Cover-Page
- `docs/screenshot_hud.png` → HUD im Kapitel "Das HUD verstehen"
- `docs/screenshot_config.png` → Config-UI im Kapitel "Config UI"
- `docs/screenshot_health_monitor.png` → Health Monitor im Kapitel "Health Monitor"

**Format:** `<img src="data:image/png;base64,..." alt="...">`

**Conversion (Shell):**
```bash
base64 -i docs/screenshot_hud.png
```

**Vorteil:** Keine externen Abhängigkeiten, File ist self-contained, schnelles Laden.

### 3. Navigation & Styling
**Gemeinsame CSS-Klassen (handbuch.html & handbuch-en.html):**
- `.sidebar` — Fixed, 260px Breite, dunkel (#2a2a2a)
- `.content` — Scrollbar mit grünem Accent (#4cbf7e)
- `.chapter` — Kapitel-Container mit Padding
- `.screenshot-frame` — Bildrahmen mit grünem Border
- `.tech-table` — Monospace-Tabelle für Tech-Specs
- `h1, h2, h3` — Grün (#4cbf7e) akzentuiert

---

## Mehrsprachiges System — Erweiterung

### Neue Sprache hinzufügen (z.B. Französisch `/handbuch-fr`)

**Schritt 1: HTML-Datei erstellen**
```bash
cp frontend/handbuch-en.html frontend/handbuch-fr.html
# Alle Inhalte ins Französische übersetzen
# WICHTIG: Screenshots bleiben identisch!
```

**Schritt 2: Button auf Cover-Page hinzufügen**
```html
<!-- In handbuch-cover.html, Zeile ~160, neben English-Button: -->
<button class="lang-button" onclick="window.location.href='/handbuch-fr'">
  🇫🇷 Français
</button>
```

**Schritt 3: Route in server.py hinzufügen**
```python
@app.get("/handbuch-fr")
async def handbook_french(request: Request):
    return FileResponse("frontend/handbuch-fr.html")
```

**Schritt 4: Testen**
```bash
curl http://localhost:8340/handbuch-fr
```

**Skalierungsnote:** Das System ist auf beliebig viele Sprachen ausgelegt. Jede Sprache = 1 HTML-Datei + 1 Route.

---

## Bild-Management

### Screenshots aktualisieren

Falls ein Screenshot veraltet ist (z.B. Health Monitor UI ändern sich):

**Schritt 1: Neues Screenshot aufnehmen**
```bash
# Screenshot-Tool verwenden (z.B. macOS Cmd+Shift+5)
# Datei speichern als: docs/screenshot_X.png
```

**Schritt 2: In Base64 konvertieren**
```python
# Python Script:
import base64

with open('docs/screenshot_health_monitor.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
    print(f"<!-- Screenshot Health Monitor -->")
    print(f"<img src='data:image/png;base64,{b64}' alt='Health Monitor'/>")
```

**Schritt 3: Im Handbuch ersetzen**
- Alte Base64-Zeichenkette in `handbuch.html` finden
- Mit neuer Zeichenkette ersetzen
- In `handbuch-en.html` ebenfalls ersetzen
- Server neu starten

### Icon-Änderung

Falls das Jarvis-Icon aktualisiert wird:

1. Neue Datei als `docs/jarvis-icon.png` speichern
2. Base64 in `handbuch-cover.html` aktualisieren (die Cover-Page zeigt das Icon)
3. Server neu starten

---

## Content-Struktur (Handbuch-Kapitel)

### Sidebar-Kategorien & Links

```
EINFÜHRUNG
├── Was ist Jarvis?
├── Systemüberblick
└── Erste Schritte

BEDIENUNG
├── Das HUD verstehen [Screenshot: HUD]
├── Sprachsteuerung
├── Alle Sprachbefehle
├── Config UI [Screenshot: Config]
├── Stimmen verwalten
└── Programme

SYSTEM
├── Architektur
├── Health Monitor [Screenshot: Health Monitor]
├── Recovery & Self-Healing
├── macOS Integration
├── Home Assistant
└── Obsidian

ENTWICKLUNG
├── Claude Code Setup
├── Logging & Diagnose
└── Performance

REFERENZ
├── Sicherheit
├── Bekannte Grenzen
├── Troubleshooting
└── Tipps & Tricks
```

### Kapitel-Vorlage

Jedes Kapitel folgt diesem Muster:

```html
<div class="chapter" id="kapitel-id">
  <h2>Kapitel-Titel</h2>
  <p>Einleitung...</p>
  
  <!-- Falls mit Screenshot: -->
  <div class="screenshot-frame">
    <img src="data:image/png;base64,..." alt="Screenshot-Beschreibung" />
    <div class="screenshot-label">Abb. X: Beschreibung</div>
  </div>
  
  <!-- Content: Absätze, Listen, Code-Blöcke: -->
  <h3>Unterkapitel</h3>
  <ul>
    <li>Punkt 1</li>
    <li>Punkt 2</li>
  </ul>
  
  <pre><code>Beispiel-Code</code></pre>
</div>
```

---

## Server-Integration (FastAPI)

### Routes in `server.py`

```python
from fastapi.responses import FileResponse

# Handbuch (Cover-Page)
@app.get("/handbuch", response_class=HTMLResponse)
async def handbook_cover():
    with open("frontend/handbuch-cover.html", "r", encoding="utf-8") as f:
        return f.read()

# Deutsches Handbuch
@app.get("/handbuch-de", response_class=HTMLResponse)
async def handbook_german():
    with open("frontend/handbuch.html", "r", encoding="utf-8") as f:
        return f.read()

# Englisches Handbuch
@app.get("/handbuch-en", response_class=HTMLResponse)
async def handbook_english():
    with open("frontend/handbuch-en.html", "r", encoding="utf-8") as f:
        return f.read()
```

**Hinweis:** Response-Type ist direkt `HTMLResponse`, nicht `FileResponse`, damit UTF-8 Encoding korrekt interpretiert wird.

---

## Performance & Optimierung

### Dateigröße

| Datei | Größe | Grund |
|---|---|---|
| handbuch-cover.html | ~7 KB | Nur Cover + SVG |
| handbuch.html (DE) | ~1.3 MB | 20 Kapitel + 4× Base64-Screenshots |
| handbuch-en.html (EN) | ~1.3 MB | Identisch zu DE |

**Ladezeit:**
- Cover-Page: <100ms
- Handbuch (inkl. Screenshots): 500–2000ms (abhängig von Internetverbindung)

### Caching-Strategie

Falls häufig aufgerufen:

```python
# Optional: Cache-Header in server.py
from datetime import datetime, timedelta

@app.get("/handbuch")
async def handbook_cover():
    with open("frontend/handbuch-cover.html", "r", encoding="utf-8") as f:
        response = HTMLResponse(content=f.read())
    response.headers["Cache-Control"] = "public, max-age=3600"  # 1h
    return response
```

---

## Wartung & Fehlersuche

### Häufige Probleme

#### Problem: Button auf Cover-Page funktioniert nicht
**Ursache:** JavaScript `window.location.href` wird blockiert  
**Lösung:** Nicht als `<a>`-Tag, sondern als `<button onclick>` implementieren (getestet, funktioniert)

#### Problem: Screenshot zeigt "Broken Image"
**Ursache:** Base64-String unvollständig oder korrupt  
**Lösung:**
```python
# Base64 validieren:
import base64
try:
    base64.b64decode(base64_string, validate=True)
    print("✓ Valid")
except:
    print("✗ Invalid")
```

#### Problem: Handbuch-Seite lädt sehr langsam
**Ursache:** Große Base64-Strings werden synchron geparst  
**Lösung:** Bilder lazy-loading: `<img src="..." loading="lazy" />`

#### Problem: Neue Sprache zeigt alte Screenshots
**Ursache:** Browser-Cache  
**Lösung:**
```bash
# Cache clearen:
curl http://localhost:8340/handbuch-fr?v=2
# Version-Parameter erzwingt Neulade
```

---

## Migrations & Rollback

### Handbuch-Version updating

Falls Inhalte veralten (z.B. neue Features):

1. **Backup erstellen:**
   ```bash
   cp frontend/handbuch.html frontend/handbuch.html.backup_20250515
   cp frontend/handbuch-en.html frontend/handbuch-en.html.backup_20250515
   ```

2. **Inhalte aktualisieren** (beides Deutsch + Englisch!)

3. **Testen:**
   ```bash
   curl -s http://localhost:8340/handbuch-de | grep "Neuer Inhalt"
   ```

4. **Bei Fehler zurückrollen:**
   ```bash
   cp frontend/handbuch.html.backup_20250515 frontend/handbuch.html
   ```

### Version-Tracking

In `version.json` (Projekt-Wurzel) eine `handbuch_version` hinzufügen:

```json
{
  "version": "2.4.0",
  "handbuch_version": "1.0.0"
}
```

---

## Dokumentations-Standards

### Content schreiben (Handbuch-Kapitel)

1. **Sprache:** Nutzer-orientiert, keine Tech-Jargon
2. **Länge:** Max. 500 Worte pro Kapitel
3. **Struktur:** Titel → Einleitung → Schritte/Details → Tipps
4. **Bilder:** Mit `.screenshot-label` beschriften
5. **Code:** In `<pre><code>` Blöcken, monospace
6. **Links:** Sind **nicht** eingebettet (statisches HTML)

### Beispiel-Kapitel

```html
<div class="chapter" id="installieren">
  <h2>Installation</h2>
  <p>Jarvis kann in 5 Schritten installiert werden.</p>
  
  <h3>Voraussetzungen</h3>
  <ul>
    <li>macOS 11+</li>
    <li>Python 3.11</li>
    <li>Anthropic API Key</li>
  </ul>
  
  <h3>Schritt 1: Repository klonen</h3>
  <pre><code>git clone https://github.com/.../jarvis-2.0.git</code></pre>
  
  <h3>Tipp</h3>
  <p><strong>💡</strong> Stelle sicher, dass Python 3.11 installiert ist.</p>
</div>
```

---

## Zusammenfassung für Wartung

| Aktion | Datei | Aufwand |
|---|---|---|
| Handbuch-Inhalte aktualisieren | `handbuch.html` + `handbuch-en.html` | ~30 min |
| Neue Sprache hinzufügen | Neue HTML + 1 Route in `server.py` | ~1-2h |
| Screenshot aktualisieren | Base64 in HTML ersetzen | ~10 min |
| Bug-Fix (z.B. Link-Fehler) | `.html` direkt editieren | ~5 min |
| Server-seitiges Caching | `server.py` Cache-Header | ~5 min |

---

## Kontakt & Fragen

Diese Dokumentation wurde am **15.05.2026** erstellt und basiert auf der Handbuch-Architektur v1.0. 

Für Fragen zur Wartung:
- Handbuch-Struktur → siehe Kapitel "Content-Struktur"
- Mehrsprachigkeit → siehe Kapitel "Mehrsprachiges System"
- Fehlersuche → siehe Kapitel "Wartung & Fehlersuche"
