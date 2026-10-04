"""Lädt alle Commons-Bilder der Karte (data/media.js, data/tours.js) einmal herunter und legt sie verkleinert
als WebP in img/ ab, damit die Seite sie schnell vom eigenen Server statt über Wikimedia lädt.
Je Bild zwei Grössen: img/<name>-480.webp (Popups) und img/<name>-960.webp (Filmmodus).
Schreibt data/images.js (Commons-Dateiname -> <name>). Schon vorhandene Bilder werden übersprungen.
    python3 tools/fetch_images.py
Benötigt: node, Pillow (pip install pillow).
"""
import hashlib, io, json, os, re, subprocess, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "img")
UA = {"User-Agent": "GebirgsfrontKarte/1.0 (https://gebirgsfront.vercel.app; Bildvorschau-Cache)"}
SIZES = (480, 960)

files = json.loads(subprocess.check_output(["node", "-e", """
global.window={};require('./data/media.js');require('./data/tours.js');
const s=new Set();
for(const g of ['forts','battles'])for(const k in window.MEDIA[g])if(window.MEDIA[g][k].img)s.add(window.MEDIA[g][k].img);
for(const t of window.TOURS)for(const st of t.steps)if(st.img)s.add(st.img);
console.log(JSON.stringify([...s]))"""], cwd=ROOT))

def slug(f):
    base = unicodedata.normalize("NFKD", os.path.splitext(f)[0]).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:40].strip("-")
    return f"{base}-{hashlib.sha1(f.encode()).hexdigest()[:6]}"

def get(url, tries=8):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or n == tries - 1:
                raise
            time.sleep(min(120, int(e.headers.get("Retry-After") or 0) or 15 * (n + 1)))

def thumb_urls(names):
    """Commons-API: URL eines vorgerenderten Vorschaubilds mit 1280 px Breite je Datei."""
    urls = {}
    for i in range(0, len(names), 40):
        q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url",
                                    "iiurlwidth": 1280, "titles": "|".join("File:" + n for n in names[i:i + 40])})
        d = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
        norm = {x["to"]: x["from"] for x in d["query"].get("normalized", [])}
        for p in d["query"]["pages"].values():
            if "imageinfo" in p:
                ii = p["imageinfo"][0]
                urls[norm.get(p["title"], p["title"])[5:]] = ii.get("thumburl") or ii["url"]
        time.sleep(2)
    return urls

os.makedirs(OUT, exist_ok=True)
names = {f: slug(f) for f in files}
todo = [f for f, s in names.items() if not all(os.path.exists(os.path.join(OUT, f"{s}-{w}.webp")) for w in SIZES)]
print(len(files), "Bilder,", len(todo), "fehlen")
urls = thumb_urls(todo) if todo else {}
missing = []
for f in todo:
    if f not in urls:
        missing.append(f); continue
    im = Image.open(io.BytesIO(get(urls[f])))
    im = im.convert("RGB")
    for w in SIZES:
        x = im if im.width <= w else im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        x.save(os.path.join(OUT, f"{names[f]}-{w}.webp"), "WEBP", quality=72, method=6)
    print("ok", names[f])
    time.sleep(1.5)

done = {f: s for f, s in names.items() if all(os.path.exists(os.path.join(OUT, f"{s}-{w}.webp")) for w in SIZES)}
with open(os.path.join(ROOT, "data", "images.js"), "w") as fh:
    fh.write("/* Lokale Kopien der Commons-Bilder (tools/fetch_images.py): Dateiname -> img/<name>-480.webp / -960.webp */\n")
    fh.write("window.IMGS=" + json.dumps(done, ensure_ascii=False, indent=0, sort_keys=True) + ";\n")
if missing:
    sys.exit("nicht gefunden: " + ", ".join(missing))
