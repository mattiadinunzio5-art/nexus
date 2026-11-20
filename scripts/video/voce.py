#!/usr/bin/env python3
"""Genera la voce fuori campo per i video NEXUS con Kokoro (gratis, locale).

Uso:
    python3 scripts/video/voce.py "Testo da leggere" uscita.mp3 [--voce bm_george] [--velocita 1.05]

Voce scelta dall'utente: bm_george (uomo, accento inglese).
Modelli in /opt/kokoro (installati dallo script di setup dell'ambiente «Nexus»).
"""
import argparse, os, subprocess, tempfile
import soundfile as sf
from kokoro_onnx import Kokoro

MODELLI = os.environ.get("KOKORO_DIR", "/opt/kokoro")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("testo"); ap.add_argument("uscita")
    ap.add_argument("--voce", default="bm_george")
    ap.add_argument("--velocita", type=float, default=1.05)
    a = ap.parse_args()
    k = Kokoro(f"{MODELLI}/kokoro-v1.0.onnx", f"{MODELLI}/voices-v1.0.bin")
    lang = "en-gb" if a.voce.startswith("b") else "en-us"
    s, sr = k.create(a.testo, voice=a.voce, speed=a.velocita, lang=lang)
    if a.uscita.endswith(".wav"):
        sf.write(a.uscita, s, sr)
    else:
        with tempfile.NamedTemporaryFile(suffix=".wav") as t:
            sf.write(t.name, s, sr)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", t.name, "-b:a", "160k", a.uscita], check=True)
    print(f"{a.uscita}: {len(s)/sr:.1f} s, voce {a.voce}")

if __name__ == "__main__":
    main()
