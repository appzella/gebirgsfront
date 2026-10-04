"""Erzeugt die Sprecherdateien der geführten Touren (audio/<tour>-0.mp3 Vorspann, audio/<tour>-<n>.mp3 Kapitel).

Stimme: Piper, de_DE-thorsten-high (https://huggingface.co/rhasspy/piper-voices).
Aufruf: python3 tools/tour_audio.py <pfad/zu/de_DE-thorsten-high.onnx>
Benötigt: pip install piper-tts, ffmpeg, node (zum Einlesen von data/tours.js).
"""
import json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = sys.argv[1] if len(sys.argv) > 1 else "de_DE-thorsten-high.onnx"

# Zahlen und Abkürzungen ausschreiben, damit die Stimme sie richtig liest
SPOKEN = [
    ("Ortler, 3905 m. Der Ortler, 3905 Meter", "Der Ortler, dreitausendneunhundertfünf Meter"),
    ("260 000", "zweihundertsechzigtausend"),
    ("12 Kilometer", "zwölf Kilometer"),
    ("15 Uhr", "fünfzehn Uhr"),
    ("15. Mai", "fünfzehnten Mai"), ("15. Juni", "fünfzehnten Juni"),
    ("4. Juni", "vierten Juni"), ("4. November", "vierten November"), ("3. November", "dritten November"),
    ("24. Oktober", "vierundzwanzigsten Oktober"), ("26. Oktober", "sechsundzwanzigsten Oktober"),
    ("17. April", "siebzehnten April"), ("9. August", "neunten August"),
    ("1915", "neunzehnhundertfünfzehn"), ("1916", "neunzehnhundertsechzehn"),
    ("1917", "neunzehnhundertsiebzehn"), ("1918", "neunzehnhundertachtzehn"),
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
def render(text, name):
    with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
        subprocess.run([sys.executable, "-m", "piper", "-m", MODEL, "-f", wav.name,
                        "--length-scale", "1.12", "--sentence-silence", "0.5"],
                       input=text.encode(), check=True, capture_output=True)
        mp3 = os.path.join(out, name + ".mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav.name,
                        "-af", "adelay=300,loudnorm=I=-18:TP=-2,apad=pad_dur=0.4",
                        "-ac", "1", "-ar", "22050", "-b:a", "64k", mp3], check=True)
    return mp3

for t in tours:
    print(render(spoken(t["t"] + ". " + t["i"]["x"]), f"{t['id']}-0"))
    for i, s in enumerate(t["steps"], 1):
        mp3 = render(spoken(s["h"] + ". " + s["x"]), f"{t['id']}-{i}")
        print(mp3)
