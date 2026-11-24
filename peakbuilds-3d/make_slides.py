"""
Macht aus den Renderings fertige Instagram-Slides (1080x1350):
- entfernt Render-Rauschen (OpenCV)
- Slide 1: Titel DE/EN oben, Wasserzeichen-Leiste unten
- Slide 2: Innenansicht + Wasserzeichen-Leiste

Aufruf:
    python3 make_slides.py renders/forest-loft "Forest Loft" "32 m² + 12 m² Galerie / gallery"
"""
import sys, os, subprocess, json, cv2

src, title, sub = sys.argv[1], sys.argv[2], sys.argv[3]
here = os.path.dirname(os.path.abspath(__file__))
wm = os.path.abspath(os.path.join(here, "..", "peakbuilds-logo", "final", "wasserzeichen-leiste-3d.png"))
out = os.path.join(src, "slides")
os.makedirs(out, exist_ok=True)

for name in ("exterior", "interior"):
    img = cv2.imread(os.path.join(src, f"{name}.png"))
    den = cv2.fastNlMeansDenoisingColored(img, None, 5, 7, 7, 21)
    cv2.imwrite(os.path.join(src, f"{name}_clean.png"), den)

CSS = """
*{margin:0;box-sizing:border-box}
body{width:1080px;height:1350px;position:relative;overflow:hidden;font-family:Inter}
.bg{position:absolute;inset:0;width:1080px;height:1350px;object-fit:cover}
.bar{position:absolute;left:0;right:0;bottom:0;height:90px;background:rgba(244,239,230,.88)}
.bar img{width:1080px;height:90px;display:block}
.title{position:absolute;left:0;right:0;top:0;padding:64px 70px 120px;
 background:linear-gradient(rgba(20,20,20,.55),rgba(20,20,20,0));color:#F4EFE6}
.k{font-size:20px;letter-spacing:4px;text-transform:uppercase;opacity:.85}
h1{font-family:Caladea;font-weight:400;font-size:84px;line-height:1;margin:14px 0 12px}
.s{font-size:28px;font-weight:300;letter-spacing:1px}
.tag{position:absolute;right:40px;top:40px;background:rgba(244,239,230,.9);color:#1E1E1E;
 font-size:20px;letter-spacing:4px;padding:10px 18px;border-radius:30px}
"""

slides = {
    "slide-1.png": (os.path.join(src, "exterior_clean.png"),
        f'<div class="title"><div class="k">Small space, big living · Wenig Platz, viel dahinter</div>'
        f'<h1>{title}</h1><div class="s">{sub}</div></div>'),
    "slide-2.png": (os.path.join(src, "interior_clean.png"),
        '<div class="tag">INSIDE · INNEN →</div>'),
}

js = []
for fname, (img, overlay) in slides.items():
    html = (f'<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
            f'<img class="bg" src="file://{os.path.abspath(img)}">{overlay}'
            f'<div class="bar"><img src="file://{wm}"></div></body></html>')
    hp = os.path.abspath(os.path.join(out, fname.replace(".png", ".html")))
    open(hp, "w").write(html)
    js.append((hp, os.path.abspath(os.path.join(out, fname))))

script = """
const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();
for (const [h,o] of %s){const p=await b.newPage({viewport:{width:1080,height:1350},deviceScaleFactor:1});
await p.goto('file://'+h);await p.waitForTimeout(400);await p.screenshot({path:o});await p.close();}
await b.close();})();
""" % json.dumps(js)
subprocess.run(["node", "-e", script], check=True)
for h, _ in js:
    os.remove(h)
print("slides ->", out)
