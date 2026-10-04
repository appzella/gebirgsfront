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

def get(url, tries=6):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or n == tries - 1:
                raise
            time.sleep(min(120, int(e.headers.get("Retry-After") or 0) or 15 * (n + 1)))

def commons_urls(name):
    """Vorschaubild mit 960 px Breite direkt auf upload.wikimedia.org (Pfad aus dem MD5 des Dateinamens),
    ohne die oft gedrosselte Commons-API; ist das Original schmaler, das Original selbst."""
    n = name.replace(" ", "_")
    h = hashlib.md5(n.encode()).hexdigest()
    q = urllib.parse.quote(n)
    return (f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/960px-{q}",
            f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{q}")

os.makedirs(OUT, exist_ok=True)
names = {f: slug(f) for f in files}
todo = [f for f, s in names.items() if not all(os.path.exists(os.path.join(OUT, f"{s}-{w}.webp")) for w in SIZES)]
print(len(files), "Bilder,", len(todo), "fehlen")
missing = []
for f in todo:
    thumb, orig = commons_urls(f)
    try:
        data = get(thumb)
    except urllib.error.HTTPError:
        try:
            data = get(orig)
        except urllib.error.HTTPError:
            missing.append(f); continue
    im = Image.open(io.BytesIO(data))
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
