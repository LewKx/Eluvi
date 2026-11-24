# peakBuilds – Forest Cube (BIM + Rendering)

Das erste KI-Haus („Holz-Modulhaus im Wald“) als echtes BIM-Modell:
2 Module (EG 6,0 × 4,0 m, OG 6,6 × 5,2 m auskragend), Luftraum mit Galerie, Eckverglasung, Gründach.

## Dateien
| Datei | Wofür |
|---|---|
| `forest-cube.ifc` | **BIM-Modell** – in Blender mit **Bonsai** öffnen |
| `bauteilliste.csv` | Bauteilliste für Excel (Hersteller/Produkt/Preis zum Ausfüllen) |
| `bauteilliste.md` | dieselbe Liste zum Lesen |
| `render_house.py` | lädt die IFC-Datei und rendert Außen- und Innenansichten |
| `make_ifc.py` | erzeugt die IFC-Datei neu (z. B. nach Maßänderungen) |
| `renders/` | fertige Bilder |

## 1. Ordner auf den Laptop holen
GitHub → Repo `lewkx/eluvi` → Branch `claude/gallant-meitner-b7ma49` → **Code → Download ZIP**,
entpacken, Ordner `peakbuilds-bim` verwenden.

## 2. Bonsai installieren (einmalig, Blender 4.2 oder neuer)
Blender → **Bearbeiten → Einstellungen → Erweiterungen (Get Extensions)** → nach **„Bonsai“** suchen → **Installieren**.

## 3. Modell öffnen und Bauteile bearbeiten
1. In Bonsai die IFC-Datei öffnen (**Datei → Öffnen → IFC-Projekt** bzw. im Bonsai-Panel „Open IFC Project“) → `forest-cube.ifc`.
2. Bauteil anklicken (z. B. „AW EG Süd“).
3. Rechts in den **Objekteigenschaften** (Bonsai-Bereich) → **Property Sets**:
   - `PB_Bauteil` → **Hersteller, Produkt, Preis_EUR, Lieferzeit_Wochen, Notiz, Status** ausfüllen
   - `Pset_WallCommon` / `Pset_WindowCommon` → U-Wert, tragend, außen …
4. Schichtaufbauten siehst du unter **Material** (z. B. „AW Holzrahmen 388“ mit 7 Schichten).
5. **Strg + S** speichert direkt in die IFC-Datei.

### Was im Modell steckt
- **Geschosse:** 00 Fundament · 01 Erdgeschoss · 02 Obergeschoss · 03 Dach
- **Wände** (IfcWall) mit Schichtaufbau, **Fenster/Türen** (IfcWindow/IfcDoor) in echten Öffnungen
- **Decken/Dach** (IfcSlab/IfcRoof) mit Aufbau, Luftraum + Treppenauge als Öffnungen
- **Treppe** (16 Steigungen), **Geländer**, **Eckstütze**, **12 Punktfundamente**, **Terrasse**
- **Räume** (IfcSpace) mit Fläche, **Möbel** als Platzhalter
- Flächen in der Bauteilliste = Bruttoflächen (ohne Abzug der Öffnungen)

## 4. Rendern am Laptop (mit Grafikkarte + Entrauscher = viel schöner)
**Variante A – in Blender:** Reiter **Scripting** → **Öffnen** → `render_house.py` → **▶ Ausführen**.
Die Bilder landen in `renders/`. *(Achtung: das Skript ersetzt die aktuelle Szene.)*

**Variante B – Terminal** (im Ordner `peakbuilds-bim`):
```
blender -b -P render_house.py -- --samples 256 --view all
```
Optionen: `--view exterior|interior|gallery|all`, `--res 2` (= 2160×2700), `--cpu`.

**Noch realistischer:** ein kostenloses HDRI (z. B. von polyhaven.com, Kategorie „forest“) in den Ordner legen und oben im Skript bei `HDRI = "dateiname.exr"` eintragen.

Falls `import ifcopenshell` fehlschlägt: Bonsai aktivieren (es bringt ifcopenshell mit) oder `pip install ifcopenshell` für Blenders Python.

## 5. Maße ändern
Oben in `make_ifc.py` (Breite, Länge, Höhen, Auskragung …) ändern →
`python make_ifc.py` (braucht `pip install ifcopenshell`) → danach neu rendern.
