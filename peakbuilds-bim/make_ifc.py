"""
peakBuilds – "Forest Cube" als BIM-Modell (IFC4)

Erzeugt forest-cube.ifc mit allen Bauteilen (Wände, Decken, Dach, Fenster,
Türen, Treppe, Geländer, Fundamente, Terrasse, Räume, Möbel) inkl.
Schichtaufbauten und Eigenschaften. Öffnen mit Blender + Bonsai (BlenderBIM).

    python make_ifc.py            -> forest-cube.ifc + bauteilliste.csv
"""
import csv, math, os
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.util.placement

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_IFC = os.path.join(HERE, "forest-cube.ifc")
OUT_CSV = os.path.join(HERE, "bauteilliste.csv")

# ---------------------------------------------------------------------------
# Maße (Meter)
# ---------------------------------------------------------------------------
T = 0.388            # Außenwand (Schichtaufbau unten)
EG = dict(x0=0.0, x1=6.0, y0=0.0, y1=4.0)        # Erdgeschoss-Modul
OG = dict(x0=0.0, x1=6.6, y0=-1.2, y1=4.0)       # Obergeschoss-Modul (Auskragung vorne + rechts)
Z_EG = 0.60          # FFB EG (Haus steht auf Punktfundamenten)
D_SLAB = 0.357       # Bodenaufbau
Z_OG = 3.55          # FFB OG
D_CEIL = 0.30        # Geschossdecke
H_OG = 2.60          # lichte Wandhöhe OG (bis UK Dach)
D_ROOF = 0.403
Z_ROOF = Z_OG + H_OG                    # UK Dach
Z_TOP = Z_ROOF + D_ROOF

f = ifcopenshell.file(schema="IFC4")
proj = api.run("root.create_entity", f, ifc_class="IfcProject", name="peakBuilds – Forest Cube")
api.run("unit.assign_unit", f, units=[
    api.run("unit.add_si_unit", f, unit_type="LENGTHUNIT"),
    api.run("unit.add_si_unit", f, unit_type="AREAUNIT"),
    api.run("unit.add_si_unit", f, unit_type="VOLUMEUNIT"),
    api.run("unit.add_si_unit", f, unit_type="PLANEANGLEUNIT")])
model = api.run("context.add_context", f, context_type="Model")
body = api.run("context.add_context", f, context_type="Model", context_identifier="Body",
               target_view="MODEL_VIEW", parent=model)

site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Grundstück")
bldg = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Forest Cube")
s_found = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="00 Fundament")
s_eg = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="01 Erdgeschoss")
s_og = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="02 Obergeschoss")
s_roof = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="03 Dach")
api.run("aggregate.assign_object", f, relating_object=proj, products=[site])
api.run("aggregate.assign_object", f, relating_object=site, products=[bldg])
api.run("aggregate.assign_object", f, relating_object=bldg, products=[s_found, s_eg, s_og, s_roof])
for s, z in ((s_found, 0.0), (s_eg, Z_EG), (s_og, Z_OG), (s_roof, Z_ROOF)):
    api.run("geometry.edit_object_placement", f, product=s, matrix=np.eye(4))
    s.Elevation = z

ROWS = []  # für die Bauteilliste


def M(x, y, z, rot_deg=0.0):
    m = np.eye(4)
    r = math.radians(rot_deg)
    m[0][0], m[0][1], m[1][0], m[1][1] = math.cos(r), -math.sin(r), math.sin(r), math.cos(r)
    m[:3, 3] = (x, y, z)
    return m


# ---------------------------------------------------------------------------
# Materialien & Typen
# ---------------------------------------------------------------------------
def layerset(name, layers):
    ls = api.run("material.add_material_set", f, name=name, set_type="IfcMaterialLayerSet")
    for mname, d, cat in layers:
        mat = api.run("material.add_material", f, name=mname, category=cat)
        lay = api.run("material.add_layer", f, layer_set=ls, material=mat)
        api.run("material.edit_layer", f, layer=lay, attributes={"LayerThickness": d, "Name": mname})
    return ls


LS_AW = layerset("AW Holzrahmen 388", [
    ("Lärche Fassadenschalung vertikal", 0.024, "wood"),
    ("Lattung / Hinterlüftung", 0.030, "wood"),
    ("Holzfaserplatte", 0.060, "insulation"),
    ("Holzständer + Zellulosedämmung", 0.200, "insulation"),
    ("OSB-Platte (Luftdichtheit)", 0.015, "wood"),
    ("Installationsebene", 0.040, "insulation"),
    ("Dreischichtplatte Fichte", 0.019, "wood"),
])
LS_FLOOR = layerset("Boden EG Holz 357", [
    ("Eiche Landhausdiele", 0.015, "wood"),
    ("Trittschalldämmung Holzfaser", 0.020, "insulation"),
    ("OSB-Platte", 0.022, "wood"),
    ("Holzbalken + Zellulosedämmung", 0.240, "insulation"),
    ("Holzfaserplatte", 0.060, "insulation"),
])
LS_CEIL = layerset("Decke OG Holz 300", [
    ("Eiche Landhausdiele", 0.015, "wood"),
    ("Trittschalldämmung Holzfaser", 0.020, "insulation"),
    ("Brettsperrholz (CLT)", 0.140, "wood"),
    ("Holzbalken / Installationsraum", 0.106, "wood"),
    ("Dreischichtplatte Fichte", 0.019, "wood"),
])
LS_ROOF = layerset("Flachdach Gründach 403", [
    ("Extensive Dachbegrünung", 0.080, "other"),
    ("EPDM-Abdichtung", 0.002, "other"),
    ("Gefälledämmung Holzfaser", 0.080, "insulation"),
    ("OSB-Platte", 0.022, "wood"),
    ("Holzbalken + Zellulosedämmung", 0.200, "insulation"),
    ("Dreischichtplatte Fichte", 0.019, "wood"),
])
MAT_GLASS = api.run("material.add_material", f, name="3-fach Verglasung, Holz-Alu-Rahmen", category="glass")
MAT_DECK = api.run("material.add_material", f, name="Lärche Terrassendiele", category="wood")
MAT_CONC = api.run("material.add_material", f, name="Beton C25/30", category="concrete")
MAT_STEEL = api.run("material.add_material", f, name="Stahl pulverbeschichtet schwarz", category="steel")
MAT_OAK = api.run("material.add_material", f, name="Eiche massiv", category="wood")
MAT_FURN = api.run("material.add_material", f, name="Möbel", category="wood")


def bauteil_pset(el, modul, **extra):
    """Eigene Eigenschaften zum Ausfüllen (Hersteller, Produkt, Preis …)."""
    ps = api.run("pset.add_pset", f, product=el, name="PB_Bauteil")
    props = {"Modul": modul, "Status": "Konzept", "Hersteller": "", "Produkt": "",
             "Preis_EUR": 0.0, "Lieferzeit_Wochen": 0, "Notiz": ""}
    props.update(extra)
    api.run("pset.edit_pset", f, pset=ps, properties=props)


def common_pset(el, name, props):
    ps = api.run("pset.add_pset", f, product=el, name=name)
    api.run("pset.edit_pset", f, pset=ps, properties=props)


def place(el, storey, matrix, rep):
    api.run("geometry.edit_object_placement", f, product=el, matrix=matrix, is_si=True)
    api.run("geometry.assign_representation", f, product=el, representation=rep)
    api.run("spatial.assign_container", f, relating_structure=storey, products=[el])


def row(el, storey, dims, material, menge, einheit):
    ROWS.append([el.is_a(), el.Name, storey.Name, dims, material, round(menge, 2), einheit])


# ---------------------------------------------------------------------------
# Wände
# ---------------------------------------------------------------------------
def wall(name, storey, x0, y0, length, rot, z0, height, modul, ext=True):
    w = api.run("root.create_entity", f, ifc_class="IfcWall", name=name, predefined_type="STANDARD")
    rep = api.run("geometry.add_wall_representation", f, context=body, length=length, height=height, thickness=T)
    place(w, storey, M(x0, y0, z0, rot), rep)
    api.run("material.assign_material", f, products=[w], material=LS_AW)
    common_pset(w, "Pset_WallCommon", {"IsExternal": ext, "LoadBearing": True, "ThermalTransmittance": 0.13,
                                       "Reference": "AW Holzrahmen 388"})
    bauteil_pset(w, modul)
    row(w, storey, f"L {length:.2f} × H {height:.2f} × D {T:.3f}", "AW Holzrahmen 388", length * height, "m²")
    return w, (x0, y0, z0, rot)


def opening_and_fill(w, wpos, name, kind, u0, width, sill, height, modul, storey, fill_u0=None, fill_width=None):
    """u0 = Abstand vom Wandanfang, sill = Brüstung über Wand-UK."""
    x0, y0, z0, rot = wpos
    r = math.radians(rot)
    ox, oy = x0 + math.cos(r) * u0, y0 + math.sin(r) * u0
    op = api.run("root.create_entity", f, ifc_class="IfcOpeningElement", name=f"Öffnung {name}")
    rep = api.run("geometry.add_wall_representation", f, context=body, length=width, height=height, thickness=T + 0.2)
    m = M(ox - math.sin(r) * -0.1, oy + math.cos(r) * -0.1, z0 + sill, rot)
    api.run("geometry.edit_object_placement", f, product=op, matrix=m, is_si=True)
    api.run("geometry.assign_representation", f, product=op, representation=rep)
    api.run("feature.add_feature", f, feature=op, element=w)

    fu0 = u0 if fill_u0 is None else fill_u0
    width = width if fill_width is None else fill_width
    ox, oy = x0 + math.cos(r) * fu0, y0 + math.sin(r) * fu0
    if kind == "window":
        el = api.run("root.create_entity", f, ifc_class="IfcWindow", name=name, predefined_type="WINDOW")
        rep = api.run("geometry.add_window_representation", f, context=body, overall_height=height,
                      overall_width=width, partition_type="SINGLE_PANEL")
        el.OverallHeight, el.OverallWidth = height, width
        common_pset(el, "Pset_WindowCommon", {"IsExternal": True, "ThermalTransmittance": 0.70,
                                             "Reference": "Holz-Alu 3-fach"})
    else:
        el = api.run("root.create_entity", f, ifc_class="IfcDoor", name=name, predefined_type="DOOR")
        rep = api.run("geometry.add_door_representation", f, context=body, overall_height=height,
                      overall_width=width, operation_type="SINGLE_SWING_LEFT")
        el.OverallHeight, el.OverallWidth = height, width
        common_pset(el, "Pset_DoorCommon", {"IsExternal": True, "ThermalTransmittance": 0.90,
                                           "Reference": "Haustür Holz-Alu mit Glas"})
    # in Wandmitte (Tiefe) setzen
    d = T * 0.45
    m = M(ox - math.sin(r) * d, oy + math.cos(r) * d, z0 + sill, rot)
    place(el, storey, m, rep)
    api.run("material.assign_material", f, products=[el], material=MAT_GLASS)
    api.run("feature.add_filling", f, opening=op, element=el)
    bauteil_pset(el, modul)
    row(el, storey, f"B {width:.2f} × H {height:.2f}", "Holz-Alu, 3-fach", width * height, "m²")
    return el


# EG: Außenmaße 6.0 × 4.0, Wände laufen gegen den Uhrzeigersinn (Dicke nach innen)
hEG = Z_OG - D_CEIL - Z_EG
eg_front, p_ef = wall("AW EG Süd (vorne)", s_eg, EG["x0"], EG["y0"], 6.0, 0, Z_EG, hEG, "EG")
eg_right, p_er = wall("AW EG Ost", s_eg, EG["x1"], EG["y0"] + T, 4.0 - 2 * T, 90, Z_EG, hEG, "EG")
eg_back, p_eb = wall("AW EG Nord", s_eg, EG["x1"], EG["y1"], 6.0, 180, Z_EG, hEG, "EG")
eg_left, p_el = wall("AW EG West", s_eg, EG["x0"], EG["y1"] - T, 4.0 - 2 * T, 270, Z_EG, hEG, "EG")

opening_and_fill(eg_front, p_ef, "Haustür", "door", 0.75, 1.0, 0.0, 2.25, "EG", s_eg)
opening_and_fill(eg_front, p_ef, "Fixverglasung Wohnen", "window", 2.30, 3.10, 0.0, 2.30, "EG", s_eg)
opening_and_fill(eg_right, p_er, "Fenster Küche Ost", "window", 1.10 - T, 1.40, 1.00, 1.20, "EG", s_eg)
opening_and_fill(eg_back, p_eb, "Fenster Nord", "window", 3.40, 1.40, 1.05, 0.90, "EG", s_eg)

# OG: Außenmaße 6.6 × 5.2 (kragt 1.2 m nach vorne und 0.6 m nach Osten aus)
og_front, p_of = wall("AW OG Süd (vorne)", s_og, OG["x0"], OG["y0"], 6.6, 0, Z_OG, H_OG, "OG")
og_right, p_or = wall("AW OG Ost", s_og, OG["x1"], OG["y0"] + T, 5.2 - 2 * T, 90, Z_OG, H_OG, "OG")
og_back, p_ob = wall("AW OG Nord", s_og, OG["x1"], OG["y1"], 6.6, 180, Z_OG, H_OG, "OG")
og_left, p_ol = wall("AW OG West", s_og, OG["x0"], OG["y1"] - T, 5.2 - 2 * T, 270, Z_OG, H_OG, "OG")

GC = T * 0.45 + 0.04  # Lage der Glasebene ab Außenkante
opening_and_fill(og_front, p_of, "Eckverglasung Süd", "window", 3.0, 3.6, 0.40, 2.05, "OG", s_og,
                 fill_width=3.6 - GC)
opening_and_fill(og_right, p_or, "Eckverglasung Ost", "window", 0.0, 2.70 - T, 0.40, 2.05, "OG", s_og,
                 fill_u0=-(T - GC), fill_width=2.70 - GC)
col = api.run("root.create_entity", f, ifc_class="IfcColumn", name="Eckstütze Glasecke", predefined_type="COLUMN")
crep = api.run("geometry.add_slab_representation", f, context=body, depth=H_OG,
               polyline=[(-0.04, -0.04), (0.04, -0.04), (0.04, 0.04), (-0.04, 0.04)])
place(col, s_og, M(6.6 - GC, -1.2 + GC, Z_OG), crep)
api.run("material.assign_material", f, products=[col], material=MAT_STEEL)
bauteil_pset(col, "OG", Notiz="Stahl 80×80 mm, schwarz")
row(col, s_og, f"80 × 80 mm, H {H_OG:.2f}", "Stahl schwarz", 1, "Stk")
opening_and_fill(og_back, p_ob, "Fenster Schlafen Nord", "window", 1.0, 2.20, 0.90, 1.30, "OG", s_og)
opening_and_fill(og_left, p_ol, "Fenster West", "window", 1.6 - T, 1.00, 0.90, 1.20, "OG", s_og)


# ---------------------------------------------------------------------------
# Decken, Dach, Terrasse, Fundamente
# ---------------------------------------------------------------------------
def slab(name, storey, poly, z_top, depth, material, ptype, modul, ifc_class="IfcSlab"):
    s = api.run("root.create_entity", f, ifc_class=ifc_class, name=name, predefined_type=ptype)
    rep = api.run("geometry.add_slab_representation", f, context=body, depth=depth, polyline=poly)
    place(s, storey, M(0, 0, z_top - depth), rep)
    api.run("material.assign_material", f, products=[s], material=material)
    area = 0.5 * abs(sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1] for i in range(len(poly))))
    bauteil_pset(s, modul)
    row(s, storey, f"Fläche {area:.1f} m² × D {depth:.3f}", getattr(material, "Name", None) or getattr(material, "LayerSetName", ""), area, "m²")
    return s


slab("Bodenplatte EG", s_eg, [(0, 0), (6.0, 0), (6.0, 4.0), (0, 4.0)], Z_EG, D_SLAB, LS_FLOOR, "FLOOR", "EG")

# Geschossdecke mit Luftraum (Galerie) + Treppenloch: Polygon mit Aussparung als L-Form
ceil_poly = [(0, -1.2), (6.6, -1.2), (6.6, 4.0), (0, 4.0)]
# Hinweis: Luftraum x 0.3–2.4 / y 0.3–4.0 (Galerie) + Treppenauge x 2.4–5.4 / y 2.9–4.0
ceil = slab("Geschossdecke OG (mit Luftraum)", s_og, ceil_poly, Z_OG, D_CEIL, LS_CEIL, "FLOOR", "OG")
for nm, (ax0, ax1, ay0, ay1) in (("Luftraum Galerie", (T, 2.4, T, 4.0 - T)), ("Treppenauge", (2.4, 5.4, 2.9, 4.0 - T))):
    op = api.run("root.create_entity", f, ifc_class="IfcOpeningElement", name=nm)
    orep = api.run("geometry.add_slab_representation", f, context=body, depth=D_CEIL + 0.2,
                   polyline=[(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)])
    api.run("geometry.edit_object_placement", f, product=op, matrix=M(0, 0, Z_OG - D_CEIL - 0.1), is_si=True)
    api.run("geometry.assign_representation", f, product=op, representation=orep)
    api.run("feature.add_feature", f, feature=op, element=ceil)

roof = api.run("root.create_entity", f, ifc_class="IfcRoof", name="Flachdach", predefined_type="FLAT_ROOF")
api.run("geometry.edit_object_placement", f, product=roof, matrix=np.eye(4))
api.run("spatial.assign_container", f, relating_structure=s_roof, products=[roof])
rs = slab("Dachplatte Gründach", s_roof, [(-0.1, -1.3), (6.7, -1.3), (6.7, 4.1), (-0.1, 4.1)], Z_TOP, D_ROOF,
          LS_ROOF, "ROOF", "Dach")
api.run("spatial.unassign_container", f, products=[rs])
api.run("aggregate.assign_object", f, relating_object=roof, products=[rs])
common_pset(rs, "Pset_SlabCommon", {"IsExternal": True, "ThermalTransmittance": 0.11})

# Attika (Dachrand) als Blechabdeckung
for nm, poly in [("Attika Süd", [(-0.1, -1.3), (6.7, -1.3), (6.7, -1.22), (-0.1, -1.22)]),
                 ("Attika Nord", [(-0.1, 4.02), (6.7, 4.02), (6.7, 4.1), (-0.1, 4.1)]),
                 ("Attika West", [(-0.1, -1.22), (-0.02, -1.22), (-0.02, 4.02), (-0.1, 4.02)]),
                 ("Attika Ost", [(6.62, -1.22), (6.7, -1.22), (6.7, 4.02), (6.62, 4.02)])]:
    slab(nm, s_roof, poly, Z_TOP + 0.12, 0.12, MAT_STEEL, "USERDEFINED", "Dach")

slab("Terrasse Süd", s_eg, [(-0.6, -2.6), (6.0, -2.6), (6.0, 0.0), (-0.6, 0.0)], Z_EG - 0.03, 0.17, MAT_DECK,
     "USERDEFINED", "Außen")
slab("Stufe Terrasse", s_eg, [(2.2, -3.1), (3.8, -3.1), (3.8, -2.6), (2.2, -2.6)], Z_EG / 2, 0.12, MAT_DECK,
     "USERDEFINED", "Außen")

for i, (x, y) in enumerate([(x, y) for x in (0.3, 3.0, 5.7) for y in (0.3, 2.0, 3.7)] +
                           [(-0.3, -2.3), (2.7, -2.3), (5.7, -2.3)]):
    ft = api.run("root.create_entity", f, ifc_class="IfcFooting", name=f"Punktfundament {i + 1:02d}",
                 predefined_type="PAD_FOOTING")
    rep = api.run("geometry.add_slab_representation", f, context=body, depth=1.1,
                  polyline=[(-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25)])
    place(ft, s_found, M(x, y, Z_EG - D_SLAB - 1.1 if y >= 0 else Z_EG - 0.20 - 1.1 + 0.0), rep)
    api.run("material.assign_material", f, products=[ft], material=MAT_CONC)
    bauteil_pset(ft, "Fundament")
    row(ft, s_found, "50 × 50 × 110 cm", "Beton C25/30", 0.5 * 0.5 * 1.1, "m³")

# ---------------------------------------------------------------------------
# Treppe + Geländer (Galerie)
# ---------------------------------------------------------------------------
st = api.run("root.create_entity", f, ifc_class="IfcStair", name="Treppe EG–OG (gerade, Eiche)",
             predefined_type="STRAIGHT_RUN_STAIR")
n = 16
rise = (Z_OG - Z_EG) / n
going = 3.0 / (n - 1)
reps = []
items = []
for i in range(n - 1):
    x = 2.4 + i * going
    prof = f.createIfcRectangleProfileDef("AREA", None, f.createIfcAxis2Placement2D(
        f.createIfcCartesianPoint((x + going / 2, 4.0 - T - 0.36)), None), going + 0.03, 0.70)
    solid = f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(
        f.createIfcCartesianPoint((0.0, 0.0, Z_EG + (i + 1) * rise - 0.05)), None, None),
        f.createIfcDirection((0.0, 0.0, 1.0)), 0.05)
    items.append(solid)
stair_rep = f.createIfcShapeRepresentation(body, "Body", "SweptSolid", items)
place(st, s_eg, np.eye(4), stair_rep)
api.run("material.assign_material", f, products=[st], material=MAT_OAK)
common_pset(st, "Pset_StairCommon", {"NumberOfRiser": n, "NumberOfTreads": n - 1,
                                     "RiserHeight": round(rise, 3), "TreadLength": round(going, 3)})
bauteil_pset(st, "EG", Notiz="Stauraum unter der Treppe möglich")
row(st, s_eg, f"{n} Steigungen à {rise * 100:.1f} cm, Auftritt {going * 100:.1f} cm", "Eiche massiv", 1, "Stk")


def railing(name, pts):
    rl = api.run("root.create_entity", f, ifc_class="IfcRailing", name=name, predefined_type="GUARDRAIL")
    rep = api.run("geometry.add_railing_representation", f, context=body,
                  railing_path=[(x, y, Z_OG) for x, y in pts], use_manual_supports=False, height=1.0)
    place(rl, s_og, np.eye(4), rep)
    api.run("material.assign_material", f, products=[rl], material=MAT_STEEL)
    common_pset(rl, "Pset_RailingCommon", {"Height": 1.0})
    bauteil_pset(rl, "OG", Notiz="Alternativ: Glasgeländer")
    L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    row(rl, s_og, f"Länge {L:.2f} m, H 1.00", "Stahl schwarz", L, "m")


railing("Geländer Galerie", [(T, T + 0.05), (2.4, T + 0.05), (2.4, 2.9), (5.4, 2.9)])

# ---------------------------------------------------------------------------
# Räume
# ---------------------------------------------------------------------------
def space(name, storey, poly, z, height):
    sp = api.run("root.create_entity", f, ifc_class="IfcSpace", name=name)
    rep = api.run("geometry.add_slab_representation", f, context=body, depth=height, polyline=poly)
    api.run("geometry.edit_object_placement", f, product=sp, matrix=M(0, 0, z), is_si=True)
    api.run("geometry.assign_representation", f, product=sp, representation=rep)
    api.run("aggregate.assign_object", f, relating_object=storey, products=[sp])
    area = 0.5 * abs(sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1] for i in range(len(poly))))
    common_pset(sp, "Pset_SpaceCommon", {"Reference": name, "NetPlannedArea": round(area, 2)})
    row(sp, storey, f"{area:.1f} m²", "-", area, "m² NF")


i = T
space("Wohnen / Kochen / Essen", s_eg, [(i, i), (6 - i, i), (6 - i, 4 - i), (i, 4 - i)], Z_EG, Z_OG - Z_EG)
space("Galerie / Schlafen", s_og, [(2.4, -1.2 + i), (6.6 - i, -1.2 + i), (6.6 - i, 2.9), (2.4, 2.9)], Z_OG, H_OG)

# ---------------------------------------------------------------------------
# Möbel (Platzhalter)
# ---------------------------------------------------------------------------
def furniture(name, storey, x0, x1, y0, y1, z0, z1, ptype="USERDEFINED"):
    fu = api.run("root.create_entity", f, ifc_class="IfcFurniture", name=name, predefined_type=ptype)
    rep = api.run("geometry.add_slab_representation", f, context=body, depth=z1 - z0,
                  polyline=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    place(fu, storey, M(0, 0, z0), rep)
    api.run("material.assign_material", f, products=[fu], material=MAT_FURN)
    bauteil_pset(fu, storey.Name[3:])
    row(fu, storey, f"{x1 - x0:.2f} × {y1 - y0:.2f} × {z1 - z0:.2f}", "-", 1, "Stk")


furniture("Küchenzeile 2.0 m", s_eg, 5.0, 5.61, 0.6, 2.6, Z_EG, Z_EG + 0.92)
furniture("Sofa", s_eg, 0.45, 1.35, 1.1, 3.2, Z_EG, Z_EG + 0.80, "SOFA")
furniture("Esstisch", s_eg, 3.0, 4.2, 1.0, 1.9, Z_EG, Z_EG + 0.75, "TABLE")
furniture("Bett 160×200", s_og, 3.6, 5.2, 0.6, 2.6, Z_OG, Z_OG + 0.45, "BED")
furniture("Einbauschrank", s_og, 2.5, 4.9, 3.0, 3.6, Z_OG, Z_OG + 2.2)

f.write(OUT_IFC)
with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh, delimiter=";")
    w.writerow(["IFC-Klasse", "Bauteil", "Geschoss", "Abmessungen", "Material / Aufbau", "Menge", "Einheit",
                "Hersteller", "Produkt", "Preis €"])
    for r in ROWS:
        w.writerow(r + ["", "", ""])
print("OK", OUT_IFC, len(ROWS), "Bauteile")
