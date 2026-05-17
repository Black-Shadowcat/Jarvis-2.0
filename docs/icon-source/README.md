# Jarvis Icon — Quellen & Prozess

## Aktuelles Icon (v2.0.0-beta)

**Datei:** `JARVIS_source_1254x1254.png`  
**Ursprung:** KI-generiert (Referenz-Design), 1254×1254 px, RGB  
**Design:** Dunkler Orb mit Cyan-Rim-Light + Wellenform + "J.A.R.V.I.S"-Schrift

---

## Icon aktualisieren

```bash
# 1. Neue Quelldatei bereitstellen (mind. 1024x1024, PNG)
# 2. Auf 1024x1024 skalieren und als Tauri-Quelle setzen:

/opt/homebrew/bin/python3.11 - <<'EOF'
from PIL import Image
img = Image.open('docs/icon-source/JARVIS_source_1254x1254.png')
img = img.resize((1024, 1024), Image.LANCZOS)
img.save('src-tauri/icons/icon.png', 'PNG')
print("Fertig:", img.size)
EOF

# 3. Alle Tauri-Icon-Größen regenerieren:
source ~/.cargo/env
cargo tauri icon src-tauri/icons/icon.png

# 4. App Bundle neu bauen und nach ~/Applications kopieren:
cargo tauri build --debug
cp -R target/debug/bundle/macos/Jarvis.app ~/Applications/
```

---

## Konzept A (programmatisch generiert)

**Datei:** `generate_icon_konzept_a.py`  
**Technologie:** numpy + PIL — generiert einen blauen 3D-Orb mit Fresnel-Highlight  
**Verwendung:**

```bash
/opt/homebrew/bin/python3.11 docs/icon-source/generate_icon_konzept_a.py
# → /tmp/jarvis_icon_1024.png
```

Danach wie oben ab Schritt 2 weiter.

---

## App Bundle erstellen / aktualisieren

Das `.app` Bundle in `~/Applications/Jarvis.app` enthält das Icon für den Dock.  
Es wird **nicht automatisch** nach `cargo build` aktualisiert — nur nach `cargo tauri build --debug`.

```bash
# Nach Code-Änderungen:
source ~/.cargo/env
cargo tauri build --debug
cp -R target/debug/bundle/macos/Jarvis.app ~/Applications/

# Dock-Icon sofort aktualisieren (ohne Neustart):
killall Dock
```

---

## Icon-Größen (generiert von cargo tauri icon)

| Datei | Größe | Verwendung |
|-------|-------|------------|
| `src-tauri/icons/icon.icns` | multi-size | macOS .app Bundle (Dock, Finder) |
| `src-tauri/icons/128x128@2x.png` | 256×256 | Retina Display |
| `src-tauri/icons/128x128.png` | 128×128 | Standard |
| `src-tauri/icons/64x64.png` | 64×64 | Kleine Ansicht |
| `src-tauri/icons/32x32.png` | 32×32 | Minimiert / Menüleiste |
| `src-tauri/icons/icon.ico` | multi-size | Windows (Fallback) |
