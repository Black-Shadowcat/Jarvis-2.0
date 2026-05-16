#!/opt/homebrew/bin/python3.11
"""
VAD Kalibrierungs-Tool für Jarvis 2.0
Misst RMS-Werte von Stille und Sprache zur Kalibrierung der Wake-Word-Erkennung
"""

import sounddevice as sd
import numpy as np
import time
import sys
import json
import os
from datetime import datetime

SAMPLE_RATE = 16000
CHUNK_DURATION = 0.1  # 100ms chunks
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

def measure_silence(duration: float = 3.0):
    """Misst RMS während Stille"""
    print(f"\n🔇 Stille messen ({duration}s) — Bitte keine Geräusche machen...")
    time.sleep(1)

    rms_values = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, blocksize=CHUNK_SIZE):
        for i in range(int(duration / CHUNK_DURATION)):
            data = sd.rec(CHUNK_SIZE, samplerate=SAMPLE_RATE, channels=1, blocking=True)
            rms = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
            rms_values.append(rms)
            sys.stdout.write(f"\r  RMS: {rms:.5f}")
            sys.stdout.flush()
            time.sleep(CHUNK_DURATION * 0.8)

    avg_rms = np.mean(rms_values)
    max_rms = np.max(rms_values)
    print(f"\n\n  📊 Stille-Statistik:")
    print(f"     Durchschnitt: {avg_rms:.5f}")
    print(f"     Maximum:     {max_rms:.5f}")
    print(f"     → Empfohlener WW_SILENCE_RMS: {max_rms * 1.2:.5f}")

    return avg_rms, max_rms

def measure_speech(duration: float = 5.0):
    """Misst RMS während Sprache"""
    print(f"\n🎤 Sprache messen ({duration}s) — Bitte sprechen Sie normal (z.B. 'Jarvis, was ist die Temperatur')...")
    time.sleep(1)

    rms_values = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, blocksize=CHUNK_SIZE):
        for i in range(int(duration / CHUNK_DURATION)):
            data = sd.rec(CHUNK_SIZE, samplerate=SAMPLE_RATE, channels=1, blocking=True)
            rms = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
            rms_values.append(rms)
            sys.stdout.write(f"\r  RMS: {rms:.5f}")
            sys.stdout.flush()
            time.sleep(CHUNK_DURATION * 0.8)

    avg_rms = np.mean(rms_values)
    min_rms = np.min(rms_values)
    print(f"\n\n  📊 Sprache-Statistik:")
    print(f"     Durchschnitt: {avg_rms:.5f}")
    print(f"     Minimum:     {min_rms:.5f}")
    print(f"     → Empfohlener WW_VOICE_RMS: {min_rms * 0.8:.5f}")

    return avg_rms, min_rms

def main():
    print("=" * 60)
    print("  JARVIS 2.0 — VAD Kalibrierungs-Tool")
    print("=" * 60)

    print("\n⚙️  Schritt 1: Stille-Referenz messen")
    silence_avg, silence_max = measure_silence(duration=3.0)

    print("\n⚙️  Schritt 2: Sprache-Referenz messen")
    speech_avg, speech_min = measure_speech(duration=5.0)

    print("\n" + "=" * 60)
    print("  📋 KALIBRIERUNGS-ERGEBNISSE")
    print("=" * 60)

    print(f"\n📌 Stille:")
    print(f"   WW_SILENCE_RMS = {silence_max * 1.2:.5f}  (max silence + 20% margin)")
    print(f"   Gemessen: avg={silence_avg:.5f}, max={silence_max:.5f}")

    print(f"\n📌 Sprache:")
    print(f"   WW_VOICE_RMS = {speech_min * 0.8:.5f}  (min speech - 20% margin)")
    print(f"   Gemessen: avg={speech_avg:.5f}, min={speech_min:.5f}")

    print(f"\n✏️  Alte Werte (MateView Monitor-Mikrofon):")
    print(f"   WW_VOICE_RMS = 0.012")
    print(f"   WW_SILENCE_RMS = 0.008")

    print(f"\n💾 Neue Werte speichern:")
    print(f"   WW_VOICE_RMS    = {speech_min * 0.8:.5f}")
    print(f"   WW_SILENCE_RMS  = {silence_max * 1.2:.5f}")

    # Speichern in data/vad_calibration.json
    calib_data = {
        "voice_rms": round(float(speech_min * 0.8), 6),
        "silence_rms": round(float(silence_max * 1.2), 6),
        "max_secs": 5.0,
        "silence_secs": 0.8,
        "cmd_silence": 1.5,
        "calibrated_at": datetime.now().isoformat(timespec="seconds"),
        "device": sd.query_devices(kind="input").get("name", "unknown") if sd.query_devices() else "unknown"
    }

    calib_path = os.path.join(os.path.dirname(__file__), "..", "data", "vad_calibration.json")
    os.makedirs(os.path.dirname(calib_path), exist_ok=True)
    with open(calib_path, "w") as f:
        json.dump(calib_data, f, indent=2)

    print(f"\n✅ Gespeichert: {calib_path}")
    print(f"   Device: {calib_data['device']}")
    print(f"   Zeit: {calib_data['calibrated_at']}")
    print("\n📝 speech_input.py liest beim nächsten Start automatisch!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Kalibrierung abgebrochen")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fehler: {e}")
        sys.exit(1)
