"""
peakBuilds – Forest Cube rendern (Blender 4.2+ mit Bonsai, oder Blender + ifcopenshell)

Lädt forest-cube.ifc, gibt allen Bauteilen realistische Materialien,
baut Wald + Licht und rendert Außen- und Innenansichten.

Am Laptop:  Blender öffnen -> Reiter "Scripting" -> Datei öffnen -> ▶ Run
Kommandozeile:
    blender -b -P render_house.py -- --samples 256 --view all

Optional: HDRI (z. B. von polyhaven.com, Kategorie "forest") neben diese
Datei legen und unten bei HDRI den Dateinamen eintragen.
"""
import bpy, bmesh, math, os, random, sys, argparse
from mathutils import Vector, Matrix

try:
    import ifcopenshell, ifcopenshell.geom
except ImportError:  # Bonsai liefert ifcopenshell mit; sonst Pfad über PB_IFC_PATH setzen
    sys.path.append(os.environ.get("PB_IFC_PATH", ""))
    import ifcopenshell, ifcopenshell.geom

FOLDER = ""   # optional: Ordnerpfad eintragen, falls das Skript die IFC-Datei nicht findet


def find_folder():
    if FOLDER:
        return FOLDER
    cands = []
    try:
        cands.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    cands += [os.path.dirname(bpy.path.abspath(t.filepath)) for t in bpy.data.texts if t.filepath]
    cands += [os.path.dirname(bpy.data.filepath), os.getcwd()]
    for c in cands:
        if c and os.path.exists(os.path.join(c, "forest-cube.ifc")):
            return c
    raise FileNotFoundError("forest-cube.ifc nicht gefunden – bitte FOLDER oben im Skript setzen.")


HERE = find_folder()
IFC = os.path.join(HERE, "forest-cube.ifc")
HDRI = ""            # z. B. "forest_slope_4k.exr" (optional)
SUN_ELEV = 7.0       # Grad, Golden Hour
SEED = 3

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--samples", type=int, default=256)
ap.add_argument("--res", type=float, default=1.0)
ap.add_argument("--view", default="all", help="all | exterior | interior | gallery")
ap.add_argument("--out", default=os.path.join(HERE, "renders"))
ap.add_argument("--cpu", action="store_true")
args = ap.parse_args(argv)
os.makedirs(args.out, exist_ok=True)
random.seed(SEED)

if bpy.app.background:
    # Kommandozeile: frische, leere Datei (ändert keine gespeicherten Einstellungen)
    bpy.ops.wm.read_homefile(use_empty=True)
else:
    # In der Blender-Oberfläche: nur die aktuelle Szene leeren – Einstellungen & Bonsai bleiben unberührt
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.worlds, bpy.data.textures):
        for block in list(coll):
            coll.remove(block)
scene = bpy.context.scene

# ---------------------------------------------------------------------------
# Materialien
# ---------------------------------------------------------------------------
def principled(name, color, rough=0.6, metal=0.0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    for k, v in kw.items():
        p.inputs[k].default_value = v
    return m


def boards(name, c1, c2, board=0.12, gap=0.008, rough=0.7, axis="xy", grain=35, bump=0.3):
    """Holzlatten mit Fugen + Farbvariation je Brett + Maserung."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    p = N["Principled BSDF"]; p.inputs["Roughness"].default_value = rough
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs[0])
    u = N.new("ShaderNodeMath"); u.operation = "ADD"
    if axis == "xy":
        L.new(sep.outputs[0], u.inputs[0]); L.new(sep.outputs[1], u.inputs[1])
    elif axis == "x":
        L.new(sep.outputs[0], u.inputs[0]); u.inputs[1].default_value = 0
    else:
        L.new(sep.outputs[1], u.inputs[0]); u.inputs[1].default_value = 0
    dv = N.new("ShaderNodeMath"); dv.operation = "DIVIDE"; dv.inputs[1].default_value = board
    L.new(u.outputs[0], dv.inputs[0])
    fl = N.new("ShaderNodeMath"); fl.operation = "FLOOR"; L.new(dv.outputs[0], fl.inputs[0])
    fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"; L.new(dv.outputs[0], fr.inputs[0])
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "1D"; L.new(fl.outputs[0], wn.inputs["W"])
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1, 1, 0.05) if axis == "xy" else (0.05, 1, 1) if axis == "x" else (1, 0.05, 1)
    L.new(tc.outputs["Object"], mp.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = grain; nz.inputs["Detail"].default_value = 8
    nz.inputs["Distortion"].default_value = 0.6
    L.new(mp.outputs[0], nz.inputs["Vector"])
    mix = N.new("ShaderNodeMath"); mix.operation = "MULTIPLY_ADD"
    L.new(wn.outputs["Value"], mix.inputs[0]); mix.inputs[1].default_value = 0.55; L.new(nz.outputs["Fac"], mix.inputs[2])
    sub = N.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = 0.3
    L.new(mix.outputs[0], sub.inputs[0])
    cl = N.new("ShaderNodeClamp"); L.new(sub.outputs[0], cl.inputs[0])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c1, 1); ramp.color_ramp.elements[1].color = (*c2, 1)
    L.new(cl.outputs[0], ramp.inputs[0])
    g = N.new("ShaderNodeMath"); g.operation = "LESS_THAN"; g.inputs[1].default_value = gap / board
    L.new(fr.outputs[0], g.inputs[0])
    mc = N.new("ShaderNodeMix"); mc.data_type = "RGBA"
    L.new(g.outputs[0], mc.inputs["Factor"]); L.new(ramp.outputs["Color"], mc.inputs[6])
    mc.inputs[7].default_value = (0.02, 0.015, 0.01, 1)
    L.new(mc.outputs[2], p.inputs["Base Color"])
    inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
    L.new(g.outputs[0], inv.inputs[1])
    hb = N.new("ShaderNodeMath"); hb.operation = "MULTIPLY_ADD"; hb.inputs[1].default_value = 0.15
    L.new(nz.outputs["Fac"], hb.inputs[0]); L.new(inv.outputs[0], hb.inputs[2])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
    L.new(hb.outputs[0], bp.inputs["Height"]); L.new(bp.outputs[0], p.inputs["Normal"])
    return m


def noise_mat(name, c1, c2, scale=3.0, rough=0.9, bump=0.5, bscale=40):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    p = N["Principled BSDF"]; p.inputs["Roughness"].default_value = rough
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 10
    r = N.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (*c1, 1); r.color_ramp.elements[1].color = (*c2, 1)
    L.new(nz.outputs["Fac"], r.inputs[0]); L.new(r.outputs[0], p.inputs["Base Color"])
    n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = bscale
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump
    L.new(n2.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs[0], p.inputs["Normal"])
    return m


def emission(name, color, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; N.remove(N["Principled BSDF"])
    e = N.new("ShaderNodeEmission"); e.inputs["Color"].default_value = (*color, 1); e.inputs["Strength"].default_value = strength
    m.node_tree.links.new(e.outputs[0], N["Material Output"].inputs[0])
    return m


MAT = dict(
    larch=boards("Lärche hell", (0.36, 0.22, 0.12), (0.66, 0.46, 0.27)),
    dark=boards("Holz dunkel lasiert", (0.035, 0.03, 0.028), (0.11, 0.09, 0.075), rough=0.6),
    ply=boards("Dreischichtplatte innen", (0.70, 0.55, 0.38), (0.86, 0.72, 0.52), board=0.6, gap=0.003, rough=0.5, grain=10, bump=0.1),
    oak=boards("Eiche Diele", (0.42, 0.28, 0.16), (0.66, 0.48, 0.30), board=0.18, gap=0.003, rough=0.4, axis="x", grain=25, bump=0.1),
    deck=boards("Lärche Terrasse", (0.30, 0.25, 0.20), (0.52, 0.43, 0.33), board=0.14, gap=0.012, rough=0.8, axis="y"),
    metal=principled("Metall schwarz", (0.02, 0.02, 0.022), 0.35, 0.8),
    frame=principled("Rahmen schwarz", (0.015, 0.015, 0.015), 0.4, 0.3),
    glass=principled("Glas", (1, 1, 1), 0.0, **{"Transmission Weight": 1.0, "IOR": 1.5}),
    concrete=noise_mat("Beton", (0.33, 0.33, 0.31), (0.45, 0.44, 0.42), 8, 0.9, 0.2),
    sedum=noise_mat("Gründach", (0.12, 0.13, 0.04), (0.30, 0.24, 0.08), 6, 1.0, 0.8, 80),
    fabric=noise_mat("Stoff beige", (0.62, 0.57, 0.48), (0.72, 0.67, 0.58), 50, 1.0, 0.2, 200),
    linen=noise_mat("Leinen", (0.80, 0.78, 0.72), (0.88, 0.86, 0.80), 50, 1.0, 0.2, 200),
    white=principled("Küche weiß matt", (0.80, 0.79, 0.75), 0.45),
    counter=principled("Arbeitsplatte", (0.06, 0.06, 0.06), 0.3),
    door=boards("Haustür", (0.05, 0.04, 0.035), (0.12, 0.10, 0.08), board=0.1, gap=0.004, axis="x"),
    lamp=emission("Licht warm", (1.0, 0.72, 0.45), 18),
    moss=noise_mat("Waldboden", (0.05, 0.07, 0.02), (0.20, 0.17, 0.06), 0.8, 1.0, 0.9, 30),
    bark=noise_mat("Kiefernrinde", (0.18, 0.08, 0.04), (0.36, 0.17, 0.08), 20, 0.9, 1.0, 60),
    needles=noise_mat("Kiefernadeln", (0.015, 0.04, 0.02), (0.05, 0.09, 0.035), 4, 0.8, 0.6, 30),
    stone=noise_mat("Trittstein", (0.25, 0.25, 0.24), (0.42, 0.41, 0.39), 12, 0.9, 0.6, 50),
    shrub=noise_mat("Farn/Busch", (0.03, 0.08, 0.02), (0.12, 0.18, 0.04), 5, 0.9, 0.8, 40),
)

# ---------------------------------------------------------------------------
# IFC laden
# ---------------------------------------------------------------------------
ifc = ifcopenshell.open(IFC)
st = ifcopenshell.geom.settings()
st.set("use-world-coords", True)
CENTER = Vector((3.3, 1.4, 3.0))


def mesh_from_shape(name, shape):
    v = shape.geometry.verts; fc = shape.geometry.faces
    verts = [(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)]
    faces = [(fc[i], fc[i + 1], fc[i + 2]) for i in range(0, len(fc), 3)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_limit(bm, angle_limit=0.01, verts=bm.verts, edges=bm.edges)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    return ob


def assign_by_face(ob, rule):
    """rule(face_center, normal) -> material key"""
    keys = []
    for poly in ob.data.polygons:
        k = rule(ob.matrix_world @ poly.center, poly.normal)
        if k not in keys:
            keys.append(k)
            ob.data.materials.append(MAT[k])
        poly.material_index = keys.index(k)


def wall_rule(outside):
    def r(c, n):
        inward = (c - Vector((CENTER.x, CENTER.y, c.z))).dot(Vector((n.x, n.y, 0))) < 0
        if abs(n.z) > 0.9:
            return "ply" if n.z < 0 else outside
        return "ply" if inward else outside
    return r


def window_mesh(el):
    """Rahmen + Glas aus Platzierung und Abmessungen (sauberer als die IFC-Geometrie)."""
    import ifcopenshell.util.placement as up
    mtx = Matrix(up.get_local_placement(el.ObjectPlacement).tolist())
    w, h = el.OverallWidth, el.OverallHeight
    fr, d = 0.07, 0.09
    parts = [(0, w, 0, fr), (0, w, h - fr, h), (0, fr, 0, h), (w - fr, w, 0, h)]
    if el.is_a("IfcWindow") and w > 2.4:  # Sprosse
        k = max(2, round(w / 1.5))
        for i in range(1, k):
            x = w * i / k; parts.append((x - 0.03, x + 0.03, 0, h))
    for (x0, x1, z0, z1) in parts:
        bpy.ops.mesh.primitive_cube_add(size=1)
        o = bpy.context.object; o.name = el.Name + " Rahmen"
        o.scale = (x1 - x0, d, z1 - z0)
        o.matrix_world = mtx @ Matrix.Translation(((x0 + x1) / 2, 0, (z0 + z1) / 2)) @ o.matrix_basis
        o.data.materials.append(MAT["frame"])
    bpy.ops.mesh.primitive_cube_add(size=1)
    g = bpy.context.object; g.name = el.Name + (" Glas" if el.is_a("IfcWindow") else " Türblatt")
    g.scale = (w - 2 * fr + 0.02, 0.02 if el.is_a("IfcWindow") else 0.06, h - 2 * fr + 0.02)
    g.matrix_world = mtx @ Matrix.Translation((w / 2, 0, h / 2)) @ g.matrix_basis
    g.data.materials.append(MAT["glass"] if el.is_a("IfcWindow") else MAT["door"])


def cube(name, loc, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object
    o.name = name; o.scale = size; o.data.materials.append(MAT[mat]); return o

for el in ifc.by_type("IfcProduct"):
    if el.is_a() in ("IfcOpeningElement", "IfcSpace", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcRoof") \
            or not el.Representation:
        continue
    if el.is_a("IfcWindow") or el.is_a("IfcDoor"):
        window_mesh(el); continue
    try:
        sh = ifcopenshell.geom.create_shape(st, el)
    except Exception as e:
        print("skip", el.Name, e); continue
    ob = mesh_from_shape(el.Name, sh)
    n = el.Name
    if el.is_a("IfcWall"):
        assign_by_face(ob, wall_rule("dark" if " EG " in n else "larch"))
    elif el.is_a("IfcSlab"):
        if "Dachplatte" in n:
            assign_by_face(ob, lambda c, nn: "sedum" if nn.z > 0.9 else "ply" if nn.z < -0.9 else "metal")
        elif "Attika" in n:
            ob.data.materials.append(MAT["metal"])
        elif "Terrasse" in n or "Stufe" in n:
            ob.data.materials.append(MAT["deck"])
        elif "Geschossdecke" in n:
            def rule(c, nn):
                inside = -0.8 < c.y < 3.62 and 0.38 < c.x < 6.22
                if nn.z > 0.9: return "oak"
                if nn.z < -0.9: return "ply" if (c.y > 0.05 and c.x < 6.0) else "larch"
                return "ply" if inside else "larch"
            assign_by_face(ob, rule)
        else:
            assign_by_face(ob, lambda c, nn: "oak" if nn.z > 0.9 else "dark")
    elif el.is_a("IfcStair"):
        ob.data.materials.append(MAT["oak"])
    elif el.is_a("IfcRailing") or el.is_a("IfcColumn"):
        ob.data.materials.append(MAT["metal"])
    elif el.is_a("IfcFooting"):
        ob.data.materials.append(MAT["concrete"])
    elif el.is_a("IfcFurniture") and "Esstisch" in n:
        bpy.data.objects.remove(ob)
        cube("Tischplatte", (3.6, 1.45, 0.6 + 0.735), (1.2, 0.85, 0.035), "oak")
        for lx in (3.08, 4.12):
            for ly in (1.1, 1.8):
                cube("Tischbein", (lx, ly, 0.6 + 0.36), (0.05, 0.05, 0.72), "metal")
    elif el.is_a("IfcFurniture"):
        key = {"Sofa": "fabric", "Bett": "linen", "Esstisch": "oak", "Küche": "white", "Einbau": "ply"}
        ob.data.materials.append(MAT[next((v for k, v in key.items() if k in n), "ply")])
        bev = ob.modifiers.new("b", "BEVEL"); bev.width = 0.02; bev.segments = 3
        if "Küche" in n:
            bpy.ops.mesh.primitive_cube_add(size=1, location=(5.305, 1.6, 0.6 + 0.94))
            t = bpy.context.object; t.scale = (0.66, 2.02, 0.04); t.data.materials.append(MAT["counter"])
    else:
        ob.data.materials.append(MAT["ply"])

# Deko + Licht innen
cube("Kissen", (0.62, 2.6, 0.6 + 0.62), (0.18, 0.45, 0.4), "linen")
cube("Teppich", (1.9, 2.0, 0.605), (1.8, 2.0, 0.01), "fabric")
cube("Decke Bett", (4.4, 1.2, 3.55 + 0.5), (1.64, 0.9, 0.06), "fabric")
for (x, y, z, r) in [(1.4, 1.35, 3.0, 0.16), (4.0, 1.4, 6.05, 0.0)]:
    if r:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=0.18, location=(x, y, z))
        bpy.context.object.data.materials.append(MAT["metal"])
        bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.8, depth=0.02, location=(x, y, z - 0.09))
        bpy.context.object.data.materials.append(MAT["lamp"])
        bpy.ops.mesh.primitive_cylinder_add(radius=0.005, depth=3.0, location=(x, y, z + 1.6))
        bpy.context.object.data.materials.append(MAT["metal"])


def light(name, kind, loc, energy, size=0.5, color=(1.0, 0.84, 0.68)):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if kind == "AREA": ld.size = size
    o = bpy.data.objects.new(name, ld); o.location = loc; scene.collection.objects.link(o); return o

light("Innen EG", "AREA", (3.0, 2.0, 3.15), 90, 2.0)
light("Pendel", "POINT", (1.4, 1.35, 2.75), 60)
light("Innen OG", "AREA", (4.3, 1.0, 6.0), 80, 2.0)
light("Küche", "AREA", (5.3, 1.6, 2.3), 40, 1.5)

# ---------------------------------------------------------------------------
# Landschaft: Waldboden, Kiefern mit hohen Stämmen, Büsche, Trittsteine
# ---------------------------------------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
g = bpy.context.object; g.data.materials.append(MAT["moss"])
sub = g.modifiers.new("s", "SUBSURF"); sub.levels = 0
bpy.ops.object.mode_set(mode="OBJECT")

for i, (x, y) in enumerate([(2.9, -3.7), (2.6, -4.7), (3.1, -5.8), (2.7, -6.9), (3.2, -8.0)]):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.36, depth=0.08, location=(x, y, 0.02))
    s = bpy.context.object; s.scale = (1.0, 0.7, 1); s.rotation_euler.z = random.random()
    s.data.materials.append(MAT["stone"])


def crown_blob(loc, r):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=loc)
    c = bpy.context.object; c.data.materials.append(MAT["needles"])
    c.scale = (1.0, 1.0, 0.55)
    tex = bpy.data.textures.get("crown") or bpy.data.textures.new("crown", "CLOUDS")
    tex.noise_scale = 0.35
    d = c.modifiers.new("d", "DISPLACE"); d.texture = tex; d.strength = r * 0.45
    return c


def pine(x, y, hgt):
    bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=hgt * 0.018, radius2=hgt * 0.006, depth=hgt,
                                    location=(x, y, hgt / 2))
    t = bpy.context.object; t.data.materials.append(MAT["bark"])
    t.rotation_euler = (random.uniform(-0.04, 0.04), random.uniform(-0.04, 0.04), 0)
    for k in range(random.randint(8, 13)):
        a = random.uniform(0, 6.28); rr = random.uniform(0.2, 1.6)
        crown_blob((x + math.cos(a) * rr, y + math.sin(a) * rr, hgt * random.uniform(0.70, 1.0)),
                   random.uniform(0.6, 1.2))


placed = 0
while placed < 170:
    a = random.uniform(0, 2 * math.pi); dist = random.uniform(6.5, 110)
    x, y = 3.3 + math.cos(a) * dist, 1.4 + math.sin(a) * dist
    if y < -4 and -14 < x < 14:   # Blickachse zur Kamera frei
        continue
    pine(x, y, random.uniform(14, 24)); placed += 1

for _ in range(160):  # Farne / Unterholz
    a = random.uniform(0, 2 * math.pi); dist = random.uniform(3.5, 25)
    x, y = 3.3 + math.cos(a) * dist, 1.4 + math.sin(a) * dist
    if -3.2 < y < 4.6 and -1.2 < x < 7.2:
        continue
    if -10 < y < -3 and 1.8 < x < 4.2:   # Weg frei
        continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=random.uniform(0.2, 0.55), location=(x, y, 0.05))
    b = bpy.context.object; b.scale.z = 0.5; b.data.materials.append(MAT["shrub"])

# ---------------------------------------------------------------------------
# Himmel / HDRI, Sonne, Kameras, Render
# ---------------------------------------------------------------------------
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
hdri_path = os.path.join(HERE, HDRI) if HDRI else ""
if hdri_path and os.path.exists(hdri_path):
    env = wn.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdri_path)
    wl.new(env.outputs[0], wn["Background"].inputs[0])
    wn["Background"].inputs["Strength"].default_value = 1.0
else:
    sky = wn.new("ShaderNodeTexSky")
    for sky_type in ("MULTIPLE_SCATTERING", "NISHITA", "SINGLE_SCATTERING", "HOSEK_WILKIE"):
        try:   # Blender 5.x hat die Himmel-Typen umbenannt
            sky.sky_type = sky_type; break
        except TypeError:
            continue
    for attr, val in (("sun_elevation", math.radians(SUN_ELEV)), ("sun_rotation", math.radians(250)),
                      ("air_density", 1.5), ("dust_density", 3.0), ("aerosol_density", 3.0)):
        if hasattr(sky, attr):
            try:
                setattr(sky, attr, val)
            except Exception:
                pass
    wl.new(sky.outputs[0], wn["Background"].inputs[0])
    wn["Background"].inputs["Strength"].default_value = 0.25

sun = bpy.data.lights.new("Sonne", "SUN"); sun.energy = 3.0; sun.color = (1.0, 0.62, 0.36); sun.angle = math.radians(2)
so = bpy.data.objects.new("Sonne", sun); scene.collection.objects.link(so)
to_sun = Vector((-0.75, -0.45, math.tan(math.radians(SUN_ELEV)))).normalized()
so.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()


def camera(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens
    co = bpy.data.objects.new(name, cd); scene.collection.objects.link(co)
    co.location = loc; co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return co


CAMS = {
    "exterior": (camera("Außen", (0.2, -13.5, 1.55), (3.3, 0.2, 3.1), 32), 0.0),
    "interior": (camera("Innen Wohnen", (4.75, 2.6, 1.6), (0.9, 0.7, 2.9), 15), -0.6),
    "gallery": (camera("Innen Galerie", (0.75, 3.2, 5.0), (6.2, -0.9, 4.4), 18), -0.3),
}

scene.render.engine = "CYCLES"
scene.cycles.samples = args.samples
scene.cycles.max_bounces = 8
scene.render.resolution_x = int(1080 * args.res); scene.render.resolution_y = int(1350 * args.res)
scene.render.image_settings.file_format = "PNG"
# GPU + Denoiser verwenden, wenn verfügbar
if not args.cpu:
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dev in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
            try:
                prefs.compute_device_type = dev; prefs.get_devices()
                if any(d.type == dev for d in prefs.devices):
                    for d in prefs.devices: d.use = True
                    scene.cycles.device = "GPU"; print("GPU:", dev); break
            except Exception:
                pass
    except Exception:
        pass
try:
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:
    scene.cycles.use_denoising = False
try:
    scene.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            scene.view_settings.look = look; break
        except TypeError:
            continue
except Exception:
    pass

views = list(CAMS) if args.view == "all" else [args.view]
for v in views:
    cam, exp = CAMS[v]
    scene.camera = cam; scene.view_settings.exposure = exp
    scene.render.filepath = os.path.join(args.out, f"{v}.png")
    try:
        bpy.ops.render.render(write_still=True)
    except RuntimeError as e:   # Blender-Build ohne Denoiser
        print("Denoiser nicht verfügbar – rendere ohne:", e)
        scene.cycles.use_denoising = False
        bpy.ops.render.render(write_still=True)
    print("RENDERED", scene.render.filepath)
