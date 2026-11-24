# peakBuilds 3D – Tiny Houses per Code

Parametrische Tiny Houses mit Galerie, gebaut und gerendert mit Blender (Python).

## Dateien
- `build_house.py` – baut Haus, Innenausbau, Landschaft, Licht und rendert Außen- + Innenansicht
- `make_slides.py` – entrauscht die Renderings und macht fertige Instagram-Slides (Titel DE/EN, Wasserzeichen)
- `renders/<haus>/slides/` – fertige Slides zum Posten

## Neues Haus
In `build_house.py` oben die Werte in `CFG` ändern (Breite, Länge, Firsthöhe, Galerietiefe, Sonnenstand …), dann:

```bash
blender -b -P build_house.py -- --out renders/<name> --view both --samples 128
python3 make_slides.py renders/<name> "<Titel>" "<m² Text>"
```

Vorschau (schnell): `--samples 16 --res 0.4`
