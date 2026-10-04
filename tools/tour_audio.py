"""Erzeugt die Sprecherdateien der geführten Touren (audio/<tour>-<schritt>.mp3).

Stimme: Piper, de_DE-thorsten-high (https://huggingface.co/rhasspy/piper-voices).
Aufruf: python3 tools/tour_audio.py <pfad/zu/de_DE-thorsten-high.onnx>
Benötigt: pip install piper-tts, ffmpeg, node (zum Einlesen von data/tours.js).
"""
import json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = sys.argv[1] if len(sys.argv) > 1 else "de_DE-thorsten-high.onnx"

# Zahlen und Abkürzungen ausschreiben, damit die Stimme sie richtig liest
SPOKEN = [
    ("k.u.k. Truppen", "österreichisch-ungarische Truppen"),
    ("4. November 1918, 15 Uhr", "vierten November neunzehnhundertachtzehn, fünfzehn Uhr"),
    ("24. Oktober um 2 Uhr", "vierundzwanzigsten Oktober um zwei Uhr"),
    ("24. Oktober 1918", "vierundzwanzigsten Oktober neunzehnhundertachtzehn"),
    ("15. Juni 1918", "fünfzehnten Juni neunzehnhundertachtzehn"),
    ("17. April 1916", "siebzehnten April neunzehnhundertsechzehn"),
    ("15. Mai 1916", "fünfzehnten Mai neunzehnhundertsechzehn"),
    ("9. August 1916", "neunten August neunzehnhundertsechzehn"),
    ("26. Oktober", "sechsundzwanzigsten Oktober"),
    ("9. November", "neunten November"),
    ("3905 m", "dreitausendneunhundertfünf Meter"),
    ("12 km", "zwölf Kilometer"),
    ("5 Tonnen", "fünf Tonnen"),
    ("1915", "neunzehnhundertfünfzehn"),
    ("1916", "neunzehnhundertsechzehn"),
    ("1917", "neunzehnhundertsiebzehn"),
    ("1918", "neunzehnhundertachtzehn"),
]

def spoken(t):
    for a, b in SPOKEN:
        t = t.replace(a, b)
    assert not re.search(r"\d", t), t
    return t

tours = json.loads(subprocess.check_output(
    ["node", "-e", "global.window={};require('./data/tours.js');console.log(JSON.stringify(window.TOURS))"], cwd=ROOT))
out = os.path.join(ROOT, "audio")
os.makedirs(out, exist_ok=True)
for t in tours:
    for i, s in enumerate(t["steps"], 1):
        text = spoken(s["h"] + ". " + s["x"])
        with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
            subprocess.run([sys.executable, "-m", "piper", "-m", MODEL, "-f", wav.name,
                            "--length-scale", "1.12", "--sentence-silence", "0.45"],
                           input=text.encode(), check=True, capture_output=True)
            mp3 = os.path.join(out, f"{t['id']}-{i}.mp3")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav.name,
                            "-af", "adelay=300,loudnorm=I=-18:TP=-2,apad=pad_dur=0.3",
                            "-ac", "1", "-ar", "22050", "-b:a", "64k", mp3], check=True)
        print(mp3)
