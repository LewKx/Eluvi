# Projekt: peakBuilds (Instagram @thepeakbuilds)

Faceless Instagram-/Etsy-Marke rund um kleine Häuser. Kommunikation mit dem User auf **Deutsch**.

## Marke
- Name: **peakBuilds**, Instagram `@thepeakbuilds`, Etsy-Name `ThePeakBuilds`
- Nische: **„Small space, big living · Wenig Platz, viel dahinter“** – Tiny Houses / kleine Modulhäuser, immer mit **Galerie**
- Inhalte: Außenansicht + Innenansicht je Haus, Captions **DE + EN**
- Logos (final): Monogramm **C4** (`peakbuilds-logo/final/monogramm-*`) und Emblem **„EST. 2026“** (`peakbuilds-logo/final/emblem-*`). Alte Entwürfe liegen in `peakbuilds-logo/archiv/` – nicht verwenden.
- Wasserzeichen-Leisten: `wasserzeichen-leiste.png` (KI-Bilder: „AI-GENERATED · KI-GENERIERT“), `wasserzeichen-leiste-3d.png` (3D-Renderings: „3D CONCEPT · 3D-KONZEPT“)
- Farben: Beige `#F4EFE6`, Schwarz `#1E1E1E`; Schriften: Caladea/Serif + Inter

## Ordner
- `peakbuilds-bim/` – **aktueller Schwerpunkt**: Haus „Forest Cube“ als IFC (Bonsai/BlenderBIM)
  - `make_ifc.py` erzeugt `forest-cube.ifc` + `bauteilliste.csv/.md` (IfcOpenShell, Einheiten: Meter)
  - `render_house.py` lädt die IFC in Blender, vergibt Materialien, Wald/Licht, rendert `exterior/interior/gallery`
    (`blender -b -P render_house.py -- --samples 256 --view all`; im UI über Scripting-Tab)
  - Eigene Property Set `PB_Bauteil` (Hersteller, Produkt, Preis_EUR, Lieferzeit_Wochen, Notiz, Status) zum Ausfüllen
- `peakbuilds-wohnung/` – Wohnküche 21 m² (4,00 × 5,25 m): `wohnkueche-21.ifc` (Möbel = je 1 IfcFurniture mit Pset `PB_Moebel`),
  `grundriss.py` (bemaßter Grundriss), `render_room.py` (Ansichten Wohnen/Küche/Draufsicht), `make_apartment.py`
- `peakbuilds-3d/` – älterer, einfacher Blender-Prototyp (Satteldach „Forest Loft“)
- `peakbuilds-content/` – Instagram-Texte, Bio, Prompts für KI-Bilder, Nischenplan

## User-Setup
- MacBook mit **Blender 5.x** + **Bonsai**; Canva gratis; arbeitet oft am Handy
- Render-Skript darf **keine** Blender-Einstellungen zurücksetzen (kein `read_factory_settings` im UI)
- Blender-5-Kompatibilität beachten (z. B. Sky-Typ `MULTIPLE_SCATTERING` statt `NISHITA`)

## Offene Ideen
- Weitere Häuser parametrisch (Alpine Loft, Lake Cabin, Urban Cube …)
- Reels: Module setzen sich zusammen (Animation)
- Etsy: Poster, Planer, Checklisten (KI-Konzepte nie als Baupläne verkaufen)
