# Wohnküche 21 m² – planen & rendern

Ein Raum **4,00 × 5,25 m = 21,0 m²**, Raumhöhe 2,80 m: Küchenzeile 270, Esstisch 120×80 mit 4 Stühlen,
Sofa 210, Couchtisch, TV-Sideboard, Garderobe, Teppich, Lampen, Pflanze.

| Datei | Wofür |
|---|---|
| `wohnkueche-21.ifc` | Modell zum Öffnen in **Blender + Bonsai** |
| `grundriss.png` / `.svg` | bemaßter Grundriss |
| `moebelliste.md` | alle Möbel mit Maßen & Position |
| `render_room.py` | rendert „Wohnen“, „Küche“, „Draufsicht“ |
| `make_apartment.py` / `grundriss.py` | erzeugen IFC bzw. Grundriss neu |

## Einrichtung ausprobieren (schnell)
1. Blender → **Datei → Öffnen** → `wohnkueche-21.ifc` (mit Bonsai)
2. Ansicht von oben: **Ziffernblock 7** (oder oben rechts auf die Z-Achse der Navigationskugel klicken)
3. Möbel anklicken → **G** = verschieben, **R** = drehen (`R 90 Enter`), **X/Y** danach = nur in eine Richtung
   - genaue Werte: `G X 0.5 Enter` = 50 cm nach rechts
4. **N** drücken → Reiter **Item**: Position & **Abmessungen** (Breite/Tiefe/Höhe) ablesen
5. Abstände messen: Werkzeugleiste links → **Measure** (Lineal) → von Kante zu Kante ziehen
6. **Cmd + S** speichert die neuen Positionen in die IFC-Datei

Gute Richtwerte: Durchgang ≥ 80–90 cm, vor der Küche ≥ 100 cm, hinter Stühlen ≥ 70 cm.

## Rendern
Datei → Neu → Allgemein → Scripting → `render_room.py` öffnen → ▶
Bilder landen in `renders/`. Oben im Skript `DAYLIGHT = False` = Abendstimmung.
