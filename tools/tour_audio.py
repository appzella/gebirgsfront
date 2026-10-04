"""Erzeugt die Sprecherdateien der geführten Touren (audio/<tour>-0.mp3 Vorspann, audio/<tour>-<n>.mp3 Kapitel).

Zwei Stimmen-Quellen:
  ElevenLabs (Standard für die Website), braucht die Umgebungsvariable ELEVENLABS_API_KEY:
    python3 tools/tour_audio.py elevenlabs --library            # deutsche Erzählstimmen aus der Stimmenbibliothek auflisten
    python3 tools/tour_audio.py elevenlabs --sample ID1,ID2     # Hörprobe je Stimme nach audio-samples/
    python3 tools/tour_audio.py elevenlabs --voice ID           # alle Tondateien erzeugen
  Piper (frei, lokal), Stimme de_DE-thorsten-high von https://huggingface.co/rhasspy/piper-voices:
    python3 tools/tour_audio.py piper --model pfad/zu/de_DE-thorsten-high.onnx
Benötigt: ffmpeg, node (zum Einlesen von data/tours.js); für Piper zusätzlich pip install piper-tts.
"""
import argparse, json, os, re, subprocess, sys, tempfile, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("engine", choices=["elevenlabs", "piper"])
ap.add_argument("--model", default="de_DE-thorsten-high.onnx", help="Piper-Stimmenmodell")
ap.add_argument("--voice", help="ElevenLabs voice_id")
ap.add_argument("--sample", help="ElevenLabs: kommagetrennte voice_ids für Hörproben")
ap.add_argument("--library", action="store_true", help="ElevenLabs: deutsche Erzählstimmen auflisten")
ap.add_argument("--only", help="nur diese Dateien, z.B. eis-1,eis-2")
args = ap.parse_args()

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

def finish(src, mp3):
    """Einheitlich abmischen: kurze Pause vorne, Lautheit angleichen, Mono 64 kbit/s."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src,
                    "-af", "adelay=300,loudnorm=I=-18:TP=-2,apad=pad_dur=0.4",
                    "-ac", "1", "-ar", "44100", "-b:a", "64k", mp3], check=True)

def piper(text, mp3, **_):
    with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
        subprocess.run([sys.executable, "-m", "piper", "-m", args.model, "-f", wav.name,
                        "--length-scale", "1.12", "--sentence-silence", "0.5"],
                       input=text.encode(), check=True, capture_output=True)
        finish(wav.name, mp3)

XI = "https://api.elevenlabs.io"
def xi(path, body=None):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY fehlt")
    req = urllib.request.Request(XI + path, data=json.dumps(body).encode() if body else None,
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def eleven(text, mp3, voice, prev=None, nxt=None):
    body = {"text": text, "model_id": "eleven_multilingual_v2",
            # ruhig und gleichmässig wie ein Dokumentarfilm-Sprecher
            "voice_settings": {"stability": 0.6, "similarity_boost": 0.8, "style": 0.15,
                               "use_speaker_boost": True, "speed": 0.95}}
    if prev: body["previous_text"] = prev
    if nxt: body["next_text"] = nxt
    audio = xi(f"/v1/text-to-speech/{voice}?output_format=mp3_44100_128", body)
    with tempfile.NamedTemporaryFile(suffix=".mp3") as raw:
        raw.write(audio); raw.flush()
        finish(raw.name, mp3)

def scenes():
    for t in tours:
        texts = [(f"{t['id']}-0", spoken(t["t"] + ". " + t["i"]["x"]))]
        texts += [(f"{t['id']}-{i}", spoken(s["h"] + ". " + s["x"])) for i, s in enumerate(t["steps"], 1)]
        for k, (name, text) in enumerate(texts):
            yield name, text, texts[k - 1][1] if k else None, texts[k + 1][1] if k + 1 < len(texts) else None

if args.engine == "elevenlabs" and args.library:
    q = urllib.parse.urlencode({"language": "de", "use_cases": "narrative_story", "page_size": 30, "sort": "usage_character_count_1y"})
    for v in json.loads(xi("/v1/shared-voices?" + q))["voices"]:
        print(v["voice_id"], v["public_owner_id"], v["name"], v.get("gender"), v.get("age"), v.get("accent"), "|", (v.get("description") or "")[:80])
    for v in json.loads(xi("/v1/voices"))["voices"]:
        print("eigene:", v["voice_id"], v["name"], v.get("labels"))
    sys.exit()
if args.engine == "elevenlabs" and args.sample:
    os.makedirs(os.path.join(ROOT, "audio-samples"), exist_ok=True)
    name, text, prev, nxt = next(s for s in scenes() if s[0] == "eis-1")
    for v in args.sample.split(","):
        eleven(text, os.path.join(ROOT, "audio-samples", f"{v}.mp3"), v)
        print("audio-samples/" + v + ".mp3")
    sys.exit()
if args.engine == "elevenlabs" and not args.voice:
    sys.exit("--voice fehlt (Stimmen mit --library suchen)")

only = set(args.only.split(",")) if args.only else None
for name, text, prev, nxt in scenes():
    if only and name not in only:
        continue
    mp3 = os.path.join(out, name + ".mp3")
    if args.engine == "piper":
        piper(text, mp3)
    else:
        eleven(text, mp3, args.voice, prev, nxt)
    print(mp3)
