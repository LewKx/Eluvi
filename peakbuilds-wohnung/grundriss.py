"""
Bemaßter Grundriss aus der IFC-Datei -> grundriss.svg (+ grundriss.png, wenn Playwright vorhanden)

    python grundriss.py
"""
import os, subprocess, json
import numpy as np
import ifcopenshell, ifcopenshell.geom

HERE = os.path.dirname(os.path.abspath(__file__))
ifc = ifcopenshell.open(os.path.join(HERE, "wohnkueche-21.ifc"))
st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)

S, PAD = 130, 150          # 1 m = 130 px
X0, X1, Y0, Y1 = -0.15, 4.15, -0.15, 5.55
W, H = int((X1 - X0) * S + 2 * PAD), int((Y1 - Y0) * S + 2 * PAD + 60)


def px(x, y):
    return PAD + (x - X0) * S, PAD + (Y1 - y) * S   # Norden oben


def bbox(el):
    v = np.array(ifcopenshell.geom.create_shape(st, el).geometry.verts).reshape(-1, 3)
    return v.min(0), v.max(0)


out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="Inter, Helvetica, sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#F4EFE6"/>']


def rect(a, b, fill="none", stroke="#1E1E1E", sw=2, extra=""):
    (xa, ya), (xb, yb) = px(a[0], b[1]), px(b[0], a[1])
    out.append(f'<rect x="{xa:.1f}" y="{ya:.1f}" width="{xb - xa:.1f}" height="{yb - ya:.1f}" '
               f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def text(x, y, s, size=15, anchor="middle", weight=400, color="#1E1E1E", rot=0):
    X, Y = px(x, y)
    t = f' transform="rotate({rot} {X:.1f} {Y:.1f})"' if rot else ""
    out.append(f'<text x="{X:.1f}" y="{Y:.1f}" font-size="{size}" text-anchor="{anchor}" '
               f'font-weight="{weight}" fill="{color}" dominant-baseline="middle"{t}>{s}</text>')


def dim(a, b, off, label, vertical=False):
    """Maßkette zwischen a und b (Meter), off = Abstand in Meter."""
    if vertical:
        x = a[0] + off
        (X, Ya), (_, Yb) = px(x, a[1]), px(x, b[1])
        out.append(f'<line x1="{X}" y1="{Ya}" x2="{X}" y2="{Yb}" stroke="#1E1E1E" stroke-width="1.5"/>')
        for Y in (Ya, Yb):
            out.append(f'<line x1="{X - 7}" y1="{Y + 7}" x2="{X + 7}" y2="{Y - 7}" stroke="#1E1E1E" stroke-width="2"/>')
        text(x - 0.12 if off < 0 else x + 0.12, (a[1] + b[1]) / 2, label, 17, rot=-90, weight=500)
    else:
        y = a[1] + off
        (Xa, Y), (Xb, _) = px(a[0], y), px(b[0], y)
        out.append(f'<line x1="{Xa}" y1="{Y}" x2="{Xb}" y2="{Y}" stroke="#1E1E1E" stroke-width="1.5"/>')
        for X in (Xa, Xb):
            out.append(f'<line x1="{X - 7}" y1="{Y + 7}" x2="{X + 7}" y2="{Y - 7}" stroke="#1E1E1E" stroke-width="2"/>')
        text((a[0] + b[0]) / 2, y + (0.12 if off > 0 else -0.12), label, 17, weight=500)


# Möbel (zuerst, damit Wände darüber liegen)
for el in ifc.by_type("IfcFurniture"):
    lo, hi = bbox(el)
    if "Teppich" in el.Name:
        rect(lo, hi, "#E6DED0", "#B9AE9C", 1, 'stroke-dasharray="6 5"')
for el in ifc.by_type("IfcFurniture"):
    if "Teppich" in el.Name or "Pendel" in el.Name:
        continue
    lo, hi = bbox(el)
    rect(lo, hi, "#FFFFFF", "#1E1E1E", 1.5)
    w_cm, d_cm = round((hi[0] - lo[0]) * 100), round((hi[1] - lo[1]) * 100)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    name = el.Name.split(" ")[0] if "Stuhl" not in el.Name else ""
    if name and min(hi[0] - lo[0], hi[1] - lo[1]) < 0.36 and "Pflanze" not in el.Name:
        name = ""
    if name:
        small = min(hi[0] - lo[0], hi[1] - lo[1]) < 0.5
        rot = -90 if (hi[1] - lo[1]) > (hi[0] - lo[0]) * 1.6 else 0
        text(cx, cy + (0.09 if not small else 0.0), name, 13 if small else 15, weight=600, rot=rot)
        if not small:
            text(cx + (0.0 if not rot else 0.17), cy - (0.12 if not rot else 0), f"{w_cm}×{d_cm}", 13,
                 color="#6b6458", rot=rot)

# Wände
for el in ifc.by_type("IfcWall"):
    lo, hi = bbox(el)
    rect(lo, hi, "#1E1E1E", "#1E1E1E", 1)

# Fenster + Tür
for el in ifc.by_type("IfcWindow"):
    lo, hi = bbox(el)
    rect((lo[0], 5.25), (hi[0], 5.55), "#F4EFE6", "#1E1E1E", 1.5)
    for y in (5.36, 5.44):
        a, b = px(lo[0], y), px(hi[0], y)
        out.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#5B8DB8" stroke-width="2"/>')
for el in ifc.by_type("IfcDoor"):
    lo, hi = bbox(el)
    rect((lo[0] + 0.03, -0.15), (hi[0] - 0.03, 0.0), "#F4EFE6", "#F4EFE6", 0)
    w = hi[0] - lo[0] - 0.06
    hx, hy = px(hi[0] - 0.03, 0.0)
    ex, ey = px(hi[0] - 0.03, w)
    sx, sy = px(lo[0] + 0.03, 0.0)
    out.append(f'<line x1="{hx}" y1="{hy}" x2="{ex}" y2="{ey}" stroke="#1E1E1E" stroke-width="2"/>')
    out.append(f'<path d="M {ex} {ey} A {w * S} {w * S} 0 0 0 {sx} {sy}" fill="none" stroke="#1E1E1E" '
               f'stroke-width="1" stroke-dasharray="5 4"/>')
    text((lo[0] + hi[0]) / 2, -0.32, f"Tür {round(el.OverallWidth*100)}", 13, color="#6b6458")

# Maße
dim((0, 5.55), (4.0, 5.55), 0.45, "4,00 m")
dim((0, -0.15), (4.0, -0.15), -0.55, "4,00 m")
dim((4.15, 0), (4.15, 5.25), 0.45, "5,25 m", vertical=True)
dim((-0.15, 0), (-0.15, 5.25), -0.45, "5,25 m", vertical=True)
for el in ifc.by_type("IfcWindow"):
    lo, hi = bbox(el)
    text((lo[0] + hi[0]) / 2, 5.73, f"Fenster {round(el.OverallWidth*100)}", 13, color="#6b6458")

text(1.6, 4.95, "Wohnküche · 21,0 m²", 20, weight=700, color="#2F5D50")
text(1.6, 4.77, "Raumhöhe 2,80 m", 14, color="#2F5D50")
out.append(f'<text x="{W/2}" y="{H - 40}" font-size="20" text-anchor="middle" letter-spacing="3" '
           f'fill="#1E1E1E">@thepeakbuilds · GRUNDRISS</text>')
out.append("</svg>")

svg = os.path.join(HERE, "grundriss.svg")
open(svg, "w", encoding="utf-8").write("\n".join(out))
png = os.path.join(HERE, "grundriss.png")
js = f"""const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();
const p=await b.newPage({{viewport:{{width:{W},height:{H}}},deviceScaleFactor:2}});
await p.goto('file://{svg}');await p.screenshot({{path:'{png}'}});await b.close();}})();"""
try:
    subprocess.run(["node", "-e", js], check=True)
    print("OK", png)
except Exception as e:
    print("SVG erstellt (PNG übersprungen):", e)
