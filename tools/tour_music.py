"""Erzeugt die Hintergrundmusik der Tour-Filme mit Google Lyria (audio/music-<tour>.mp3).
Schlüssel als GEMINI_API_KEY oder als Zugangsdaten der Umgebung (Header x-goog-api-key).
    python3 tools/tour_music.py                # alle Touren
    python3 tools/tour_music.py --only eis     # nur diese
Die Stücke laufen auf der Seite in Schleife, leise unter dem Sprecher. Benötigt: ffmpeg.
"""
import argparse, base64, json, os, subprocess, sys, tempfile, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://generativelanguage.googleapis.com/v1beta/models/lyria-3-pro-preview:generateContent"
BASE = ("Instrumental underscore for a historical documentary about the First World War on the Alpine front between "
        "Austria-Hungary and Italy. No vocals, no modern drums or synths. Quiet and restrained so a narrator can speak "
        "over it, gentle swells, about two and a half minutes, with an ending that can loop back to the beginning. ")
MOOD = {
    "eis": "Soldiers fighting on glaciers and high peaks, 1915-1918. Slow, sombre and reverent, about 60 BPM, D minor. "
           "Sustained low strings, a sparse solo piano melody, a distant solo horn, soft cold wind texture.",
    "straf": "The Austro-Hungarian spring offensive of 1916 against the Italian plateaus of Asiago, with mountain fortresses "
             "and heavy artillery. Tense and grave, about 70 BPM, C minor. Low cello ostinato, muted brass, distant soft timpani rolls.",
    "isonzo": "Eleven battles along the emerald Isonzo river and the barren Karst plateau, endless attrition. Mournful and "
              "intimate, about 56 BPM, A minor. Solo cello lament over soft string pads, sparse harp notes like water.",
    "karfreit": "The breakthrough at Caporetto in October 1917: gas and fog in the valleys before dawn, then a sudden collapse "
                "and a long retreat. Suspenseful and dark, about 66 BPM, E minor. Pulsing low strings, eerie high violin "
                "harmonics, muffled bass drum, rising tension that dissolves into weariness.",
    "piave": "The last year of the war on the Piave river and Monte Grappa, ending with the armistice of November 1918. "
             "Elegiac and dignified, slowly turning towards peace and hope, about 58 BPM, F major with minor shadows. "
             "Warm strings, solo piano, a soft trumpet melody near the end.",
}

ap = argparse.ArgumentParser()
ap.add_argument("--only", help="kommagetrennte Tour-IDs")
args = ap.parse_args()

headers = {"Content-Type": "application/json"}
if os.environ.get("GEMINI_API_KEY"):
    headers["x-goog-api-key"] = os.environ["GEMINI_API_KEY"]

for tid, mood in MOOD.items():
    if args.only and tid not in args.only.split(","):
        continue
    body = {"contents": [{"parts": [{"text": BASE + mood}]}]}
    for wait in (20, 60, 0):
        try:
            req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=headers)
            with urllib.request.urlopen(req, timeout=600) as r:
                parts = json.load(r)["candidates"][0]["content"]["parts"]
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 503) or not wait:
                sys.exit(f"Lyria {e.code}: {e.read()[:300]}")
            time.sleep(wait)
    data = next(base64.b64decode(p["inlineData"]["data"]) for p in parts if "inlineData" in p)
    with tempfile.NamedTemporaryFile(suffix=".mp3") as raw:
        raw.write(data); raw.flush()
        # einheitlich leise abmischen, Stereo 96 kbit/s, weiche Ein- und Ausblendung für die Schleife
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", raw.name]))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw.name, "-af",
                        f"loudnorm=I=-20:TP=-2,afade=t=in:d=2,afade=t=out:st={dur - 4:.2f}:d=4",
                        "-ar", "44100", "-b:a", "96k", os.path.join(ROOT, "audio", f"music-{tid}.mp3")], check=True)
    print(f"audio/music-{tid}.mp3", round(dur), "s")
