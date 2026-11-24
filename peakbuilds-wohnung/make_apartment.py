"""
peakBuilds – Wohnung "Wohnküche 21 m²" als IFC (für Blender + Bonsai)

Ein Raum 4,00 × 5,25 m (= 21,0 m²), Wohnküche mit Essplatz und Wohnbereich.
Jedes Möbel ist EIN Objekt (IfcFurniture) mit echten Maßen -> in Blender
einfach anklicken, mit G verschieben, mit R drehen, Maße in der N-Leiste.

    python make_apartment.py   ->  wohnkueche-21.ifc + moebelliste.md
"""
import math, os
import numpy as np
import ifcopenshell
import ifcopenshell.api as api

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "wohnkueche-21.ifc")

# ---------------------------------------------------------------------------
# Raum
# ---------------------------------------------------------------------------
RX, RY = 4.00, 5.25      # Innenmaße (Breite × Länge) -> 21,0 m²
H = 2.80                 # Raumhöhe
TW, TI = 0.30, 0.15      # Außenwand (Fensterseite) / Innenwände

f = ifcopenshell.file(schema="IFC4")
proj = api.run("root.create_entity", f, ifc_class="IfcProject", name="peakBuilds – Wohnküche 21 m²")
api.run("unit.assign_unit", f, units=[api.run("unit.add_si_unit", f, unit_type=t)
                                      for t in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT", "PLANEANGLEUNIT")])
ctx = api.run("context.add_context", f, context_type="Model")
body = api.run("context.add_context", f, context_type="Model", context_identifier="Body",
               target_view="MODEL_VIEW", parent=ctx)
site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Grundstück")
bldg = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Wohnhaus")
storey = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Wohnung")
api.run("aggregate.assign_object", f, relating_object=proj, products=[site])
api.run("aggregate.assign_object", f, relating_object=site, products=[bldg])
api.run("aggregate.assign_object", f, relating_object=bldg, products=[storey])
for o in (site, bldg, storey):
    api.run("geometry.edit_object_placement", f, product=o, matrix=np.eye(4))

# ---------------------------------------------------------------------------
# Oberflächen (Farben sieht man auch direkt in Bonsai)
# ---------------------------------------------------------------------------
STYLE_COLORS = {
    "eiche": (0.62, 0.45, 0.28), "weiss": (0.92, 0.91, 0.88), "wand": (0.93, 0.92, 0.89),
    "stoff": (0.66, 0.63, 0.56), "stoff_gruen": (0.32, 0.38, 0.30), "schwarz": (0.06, 0.06, 0.06),
    "arbeitsplatte": (0.20, 0.20, 0.20), "front": (0.78, 0.76, 0.70), "glas": (0.75, 0.85, 0.9),
    "edelstahl": (0.6, 0.6, 0.6), "teppich": (0.80, 0.76, 0.68), "pflanze": (0.15, 0.32, 0.12),
    "topf": (0.55, 0.35, 0.25), "licht": (1.0, 0.85, 0.6),
}
STYLES = {}
for n, c in STYLE_COLORS.items():
    st = api.run("style.add_style", f, name=n)
    api.run("style.add_surface_style", f, style=st, ifc_class="IfcSurfaceStyleShading",
            attributes={"SurfaceColour": {"Name": None, "Red": c[0], "Green": c[1], "Blue": c[2]}})
    STYLES[n] = st


def M(x, y, z=0.0, rot=0.0):
    m = np.eye(4); r = math.radians(rot)
    m[0][0], m[0][1], m[1][0], m[1][1] = math.cos(r), -math.sin(r), math.sin(r), math.cos(r)
    m[:3, 3] = (x, y, z)
    return m


def box_item(x0, y0, z0, dx, dy, dz):
    prof = f.createIfcRectangleProfileDef("AREA", None, f.createIfcAxis2Placement2D(
        f.createIfcCartesianPoint((x0 + dx / 2, y0 + dy / 2)), None), dx, dy)
    return f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(
        f.createIfcCartesianPoint((0.0, 0.0, z0)), None, None), f.createIfcDirection((0.0, 0.0, 1.0)), dz)


def cyl_item(cx, cy, z0, r, dz):
    prof = f.createIfcCircleProfileDef("AREA", None, f.createIfcAxis2Placement2D(
        f.createIfcCartesianPoint((cx, cy)), None), r)
    return f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(
        f.createIfcCartesianPoint((0.0, 0.0, z0)), None, None), f.createIfcDirection((0.0, 0.0, 1.0)), dz)


def styled_rep(parts):
    """parts: Liste von (item, stilname)"""
    rep = f.createIfcShapeRepresentation(body, "Body", "SweptSolid", [p[0] for p in parts])
    for item, sname in parts:
        api.run("style.assign_item_style", f, item=item, style=STYLES[sname])
    return rep


MOEBEL = []


def furniture(name, ptype, x, y, rot, size, parts, note=""):
    """x,y = Position der linken unteren Ecke (von oben gesehen), rot in Grad, size = (B, T, H)."""
    el = api.run("root.create_entity", f, ifc_class="IfcFurniture", name=name, predefined_type=ptype)
    api.run("geometry.edit_object_placement", f, product=el, matrix=M(x, y, 0, rot), is_si=True)
    api.run("geometry.assign_representation", f, product=el, representation=styled_rep(parts))
    api.run("spatial.assign_container", f, relating_structure=storey, products=[el])
    ps = api.run("pset.add_pset", f, product=el, name="PB_Moebel")
    api.run("pset.edit_pset", f, pset=ps, properties={
        "Breite_cm": round(size[0] * 100), "Tiefe_cm": round(size[1] * 100), "Hoehe_cm": round(size[2] * 100),
        "Hersteller": "", "Produkt": "", "Preis_EUR": 0.0, "Link": "", "Notiz": note})
    MOEBEL.append((name, size, (x, y), rot, note))
    return el


# ---------------------------------------------------------------------------
# Wände, Boden, Decke, Tür, Fenster
# ---------------------------------------------------------------------------
LS = api.run("material.add_material_set", f, name="Innenwand verputzt", set_type="IfcMaterialLayerSet")
api.run("material.edit_layer", f, layer=api.run("material.add_layer", f, layer_set=LS,
        material=api.run("material.add_material", f, name="Mauerwerk verputzt", category="brick")),
        attributes={"LayerThickness": TI})


def wall(name, x, y, length, rot, t):
    w = api.run("root.create_entity", f, ifc_class="IfcWall", name=name)
    rep = api.run("geometry.add_wall_representation", f, context=body, length=length, height=H, thickness=t)
    api.run("style.assign_representation_styles", f, shape_representation=rep, styles=[STYLES["wand"]])
    api.run("geometry.edit_object_placement", f, product=w, matrix=M(x, y, 0, rot), is_si=True)
    api.run("geometry.assign_representation", f, product=w, representation=rep)
    api.run("spatial.assign_container", f, relating_structure=storey, products=[w])
    return w, (x, y, rot, t)


# Wände außen um den Innenraum (Innenmaß bleibt exakt 4,00 × 5,25)
w_s, p_s = wall("Wand Eingang (Süd)", -TI, -TI, RX + 2 * TI, 0, TI)
w_n, p_n = wall("Außenwand Fenster (Nord)", RX + TI, RY + TW, RX + 2 * TI, 180, TW)
w_e, p_e = wall("Wand Ost", RX + TI, 0, RY, 90, TI)
w_w, p_w = wall("Wand West", -TI, RY, RY, 270, TI)


def opening(w, pos, name, kind, u0, width, sill, height):
    x, y, rot, t = pos
    r = math.radians(rot)
    ox, oy = x + math.cos(r) * u0, y + math.sin(r) * u0
    op = api.run("root.create_entity", f, ifc_class="IfcOpeningElement", name="Öffnung " + name)
    rep = api.run("geometry.add_wall_representation", f, context=body, length=width, height=height, thickness=t + 0.2)
    api.run("geometry.edit_object_placement", f, product=op,
            matrix=M(ox + math.sin(r) * 0.1, oy - math.cos(r) * 0.1, sill, rot), is_si=True)
    api.run("geometry.assign_representation", f, product=op, representation=rep)
    api.run("feature.add_feature", f, feature=op, element=w)
    cls = "IfcWindow" if kind == "window" else "IfcDoor"
    el = api.run("root.create_entity", f, ifc_class=cls, name=name)
    if kind == "window":
        rep = api.run("geometry.add_window_representation", f, context=body, overall_height=height,
                      overall_width=width, partition_type="DOUBLE_PANEL_VERTICAL",
                      panel_properties=[{}, {}])
    else:
        rep = api.run("geometry.add_door_representation", f, context=body, overall_height=height,
                      overall_width=width, operation_type="SINGLE_SWING_RIGHT")
    el.OverallWidth, el.OverallHeight = width, height
    d = t * 0.5
    api.run("geometry.edit_object_placement", f, product=el,
            matrix=M(ox - math.sin(r) * d, oy + math.cos(r) * d, sill, rot), is_si=True)
    api.run("geometry.assign_representation", f, product=el, representation=rep)
    api.run("spatial.assign_container", f, relating_structure=storey, products=[el])
    api.run("feature.add_filling", f, opening=op, element=el)


opening(w_s, p_s, "Eingangstür", "door", TI + 2.95, 0.90, 0.0, 2.10)
opening(w_n, p_n, "Fenster links", "window", TI + 0.55, 1.20, 0.85, 1.60)     # Wand läuft von Ost nach West
opening(w_n, p_n, "Fenster rechts", "window", TI + 2.25, 1.20, 0.85, 1.60)


def slab(name, z_top, d, style, ptype):
    s = api.run("root.create_entity", f, ifc_class="IfcSlab", name=name, predefined_type=ptype)
    rep = api.run("geometry.add_slab_representation", f, context=body, depth=d,
                  polyline=[(-TI, -TI), (RX + TI, -TI), (RX + TI, RY + TW), (-TI, RY + TW)])
    api.run("style.assign_representation_styles", f, shape_representation=rep, styles=[STYLES[style]])
    api.run("geometry.edit_object_placement", f, product=s, matrix=M(0, 0, z_top - d), is_si=True)
    api.run("geometry.assign_representation", f, product=s, representation=rep)
    api.run("spatial.assign_container", f, relating_structure=storey, products=[s])


slab("Boden Eiche Fischgrät", 0.0, 0.20, "eiche", "FLOOR")
slab("Decke", H + 0.20, 0.20, "weiss", "ROOF")

sp = api.run("root.create_entity", f, ifc_class="IfcSpace", name="Wohnküche")
rep = api.run("geometry.add_slab_representation", f, context=body, depth=H,
              polyline=[(0, 0), (RX, 0), (RX, RY), (0, RY)])
api.run("geometry.edit_object_placement", f, product=sp, matrix=np.eye(4))
api.run("geometry.assign_representation", f, product=sp, representation=rep)
api.run("aggregate.assign_object", f, relating_object=storey, products=[sp])
ps = api.run("pset.add_pset", f, product=sp, name="Pset_SpaceCommon")
api.run("pset.edit_pset", f, pset=ps, properties={"NetPlannedArea": round(RX * RY, 2)})

# ---------------------------------------------------------------------------
# Möbel (lokale Koordinaten: x = Breite, y = Tiefe, Rückseite bei y = Tiefe)
# ---------------------------------------------------------------------------
# Küchenzeile 2,70 m an der Westwand (Rücken zur Wand), mit Hochschrank, Spüle, Kochfeld, Oberschränken
kw, kd = 2.70, 0.62
parts = [
    (box_item(0, 0.02, 0.0, 0.60, 0.60, 2.15), "front"),                 # Hochschrank (Kühlschrank)
    (box_item(0.60, 0.05, 0.0, kw - 0.60, 0.55, 0.10), "schwarz"),        # Sockel
    (box_item(0.60, 0.02, 0.10, kw - 0.60, 0.58, 0.76), "front"),         # Unterschränke
    (box_item(0.60, 0.0, 0.86, kw - 0.60, kd, 0.04), "arbeitsplatte"),    # Arbeitsplatte
    (box_item(1.05, 0.10, 0.84, 0.50, 0.40, 0.03), "edelstahl"),          # Spüle
    (box_item(1.85, 0.08, 0.90, 0.60, 0.50, 0.005), "schwarz"),           # Kochfeld
    (box_item(0.60, 0.27, 1.45, kw - 0.60, 0.35, 0.72), "front"),         # Oberschränke
    (box_item(0.60, 0.30, 1.42, kw - 0.60, 0.30, 0.02), "licht"),         # LED unter Oberschrank
]
furniture("Küchenzeile 270 cm", "USERDEFINED", kd, 0.0, 90, (kw, kd, 2.17), parts,
          "Hochschrank mit Kühlschrank, Spüle, Induktion, Oberschränke")

# Esstisch 120 × 80 + 4 Stühle
def table(w, d, h, top="eiche"):
    p = [(box_item(0, 0, h - 0.03, w, d, 0.03), top)]
    for lx, ly in ((0.05, 0.05), (w - 0.09, 0.05), (0.05, d - 0.09), (w - 0.09, d - 0.09)):
        p.append((box_item(lx, ly, 0, 0.04, 0.04, h - 0.03), "schwarz"))
    return p


furniture("Esstisch 120×80", "TABLE", 1.60, 1.20, 0, (1.20, 0.80, 0.75), table(1.20, 0.80, 0.75))


def chair():
    p = [(box_item(0, 0, 0.44, 0.44, 0.44, 0.03), "eiche"),
         (box_item(0, 0.40, 0.47, 0.44, 0.04, 0.38), "eiche")]
    for lx, ly in ((0.02, 0.02), (0.39, 0.02), (0.02, 0.39), (0.39, 0.39)):
        p.append((box_item(lx, ly, 0, 0.03, 0.03, 0.44), "schwarz"))
    return p


for i, (x, y, r) in enumerate([(2.17, 1.15, 180), (2.67, 1.15, 180), (1.73, 2.05, 0), (2.23, 2.05, 0)]):
    furniture(f"Stuhl {i + 1}", "CHAIR", x, y, r, (0.44, 0.44, 0.85), chair())

# Garderobe beim Eingang (Ostwand)
furniture("Garderobe / Schuhschrank", "USERDEFINED", RX - 0.40, 2.25, 270, (1.20, 0.40, 1.90),
          [(box_item(0, 0.0, 0.0, 1.20, 0.40, 0.90), "weiss"),
           (box_item(0, 0.30, 1.60, 1.20, 0.10, 0.03), "eiche"),
           (box_item(0.1, 0.36, 1.10, 1.0, 0.04, 0.5), "eiche")], "Schuhschrank + Hakenleiste")

# Sofa 210 × 90 an der Ostwand, Blick Richtung Westen (TV)
sw, sd = 2.10, 0.92
sofa = [(box_item(0, 0, 0.12, sw, sd, 0.30), "stoff"),
        (box_item(0, sd - 0.20, 0.42, sw, 0.20, 0.40), "stoff"),
        (box_item(0, 0, 0.42, 0.18, sd, 0.20), "stoff"), (box_item(sw - 0.18, 0, 0.42, 0.18, sd, 0.20), "stoff"),
        (box_item(0.18, 0.02, 0.42, (sw - 0.36) / 2 - 0.01, sd - 0.24, 0.12), "stoff"),
        (box_item(sw / 2 + 0.01, 0.02, 0.42, (sw - 0.36) / 2 - 0.01, sd - 0.24, 0.12), "stoff"),
        (box_item(0.25, sd - 0.35, 0.55, 0.45, 0.14, 0.38), "stoff_gruen")]
for lx in (0.05, sw - 0.09):
    for ly in (0.05, sd - 0.09):
        sofa.append((box_item(lx, ly, 0, 0.04, 0.04, 0.12), "schwarz"))
furniture("Sofa 3-Sitzer 210", "SOFA", RX - sd, 2.95 + sw, 270, (sw, sd, 0.82), sofa)

furniture("Couchtisch Ø70", "TABLE", 2.15, 3.65, 0, (0.70, 0.70, 0.40),
          [(cyl_item(0.35, 0.35, 0.36, 0.35, 0.04), "eiche"), (cyl_item(0.35, 0.35, 0.0, 0.05, 0.36), "schwarz")])
furniture("Teppich 200×250", "USERDEFINED", 0.90, 2.65, 0, (2.00, 2.50, 0.01),
          [(box_item(0, 0, 0.0, 2.00, 2.50, 0.012), "teppich")])
furniture("TV-Sideboard 160", "USERDEFINED", 0.45, 3.00, 90, (1.60, 0.45, 0.50),
          [(box_item(0, 0, 0.10, 1.60, 0.45, 0.40), "eiche"),
           (box_item(0.05, 0.05, 0, 0.04, 0.04, 0.10), "schwarz"), (box_item(1.51, 0.05, 0, 0.04, 0.04, 0.10), "schwarz"),
           (box_item(0.25, 0.36, 0.95, 1.10, 0.04, 0.63), "schwarz")], "inkl. TV 50\" an der Wand")
furniture("Stehlampe", "USERDEFINED", 3.55, 2.55, 0, (0.35, 0.35, 1.60),
          [(cyl_item(0.175, 0.175, 0.0, 0.14, 0.02), "schwarz"), (cyl_item(0.175, 0.175, 0.02, 0.012, 1.40), "schwarz"),
           (cyl_item(0.175, 0.175, 1.40, 0.17, 0.25), "licht")])
furniture("Pflanze groß", "USERDEFINED", 0.10, 4.75, 0, (0.45, 0.45, 1.50),
          [(cyl_item(0.225, 0.225, 0.0, 0.18, 0.40), "topf"), (cyl_item(0.225, 0.225, 0.40, 0.22, 1.10), "pflanze")])
furniture("Pendelleuchte Esstisch", "USERDEFINED", 2.05, 1.45, 0, (0.30, 0.30, 0.20),
          [(cyl_item(0.15, 0.15, 1.65, 0.15, 0.18), "schwarz"), (cyl_item(0.15, 0.15, 1.64, 0.12, 0.012), "licht"),
           (cyl_item(0.15, 0.15, 1.83, 0.006, H - 1.83), "schwarz")])

f.write(OUT)

# Möbelliste
with open(os.path.join(HERE, "moebelliste.md"), "w", encoding="utf-8") as fh:
    fh.write(f"# Möbelliste – Wohnküche {RX:.2f} × {RY:.2f} m = {RX * RY:.1f} m², Raumhöhe {H:.2f} m\n\n")
    fh.write("| Möbel | B × T × H (cm) | Position (x / y in m) | Drehung | Notiz |\n|---|---|---|---|---|\n")
    for n, s, (x, y), r, note in MOEBEL:
        fh.write(f"| {n} | {s[0]*100:.0f} × {s[1]*100:.0f} × {s[2]*100:.0f} | {x:.2f} / {y:.2f} | {r}° | {note} |\n")
print("OK", OUT, len(MOEBEL), "Möbel")
