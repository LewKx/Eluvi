"""
peakBuilds – Wohnküche rendern (Blender 4.2+/5.x, mit Bonsai oder ifcopenshell)

Lädt wohnkueche-21.ifc, gibt Wänden/Boden/Möbeln realistische Materialien
und rendert: Ansicht Wohnen, Ansicht Küche, Draufsicht (Grundriss 3D).

UI:        Datei -> Neu -> Allgemein, dann Scripting -> render_room.py öffnen -> ▶
Terminal:  blender -b -P render_room.py -- --samples 256 --view all
"""
import bpy, bmesh, math, os, sys, argparse
from mathutils import Vector, Matrix

try:
    import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.placement
except ImportError:
    sys.path.append(os.environ.get("PB_IFC_PATH", ""))
    import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.placement

FOLDER = ""        # optional: Ordnerpfad, falls die IFC-Datei nicht gefunden wird
IFC_NAME = "wohnkueche-21.ifc"
DAYLIGHT = True    # False = Abendstimmung mit Lampen


def find_folder():
    if FOLDER:
        return FOLDER
    c = []
    try:
        c.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    c += [os.path.dirname(bpy.path.abspath(t.filepath)) for t in bpy.data.texts if t.filepath]
    c += [os.path.dirname(bpy.data.filepath), os.getcwd()]
    for d in c:
        if d and os.path.exists(os.path.join(d, IFC_NAME)):
            return d
    raise FileNotFoundError(IFC_NAME + " nicht gefunden – bitte FOLDER oben setzen.")


HERE = find_folder()
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--samples", type=int, default=256)
ap.add_argument("--res", type=float, default=1.0)
ap.add_argument("--view", default="all", help="all | wohnen | kueche | draufsicht")
ap.add_argument("--out", default=os.path.join(HERE, "renders"))
ap.add_argument("--cpu", action="store_true")
args = ap.parse_args(argv)
os.makedirs(args.out, exist_ok=True)

# Szene leeren (Einstellungen/Add-ons bleiben unberührt)
if bpy.app.background:
    bpy.ops.wm.read_homefile(use_empty=True)
else:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.worlds, bpy.data.textures):
        for b in list(coll):
            coll.remove(b)
scene = bpy.context.scene

# ---------------------------------------------------------------------------
# Materialien
# ---------------------------------------------------------------------------
def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes["Principled BSDF"]


def plain(name, color, rough=0.5, metal=0.0, **kw):
    m, N, L, p = node_mat(name)
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metal
    for k, v in kw.items():
        try: p.inputs[k].default_value = v
        except KeyError: pass
    return m


def noisy(name, c1, c2, scale=5, rough=0.8, bump=0.15, bscale=300, metal=0.0):
    m, N, L, p = node_mat(name)
    p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metal
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 8
    r = N.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (*c1, 1); r.color_ramp.elements[1].color = (*c2, 1)
    L.new(nz.outputs["Fac"], r.inputs[0]); L.new(r.outputs[0], p.inputs["Base Color"])
    n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = bscale
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump
    L.new(n2.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs[0], p.inputs["Normal"])
    return m


def wood(name, c1, c2, board=0.14, gap=0.002, rough=0.45, grain=30):
    """Dielen/Holz: Bretter entlang X mit Farbvariation und Maserung."""
    m, N, L, p = node_mat(name)
    p.inputs["Roughness"].default_value = rough
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    dv = N.new("ShaderNodeMath"); dv.operation = "DIVIDE"; dv.inputs[1].default_value = board
    L.new(sep.outputs[1], dv.inputs[0])
    fl = N.new("ShaderNodeMath"); fl.operation = "FLOOR"; L.new(dv.outputs[0], fl.inputs[0])
    fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"; L.new(dv.outputs[0], fr.inputs[0])
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "1D"; L.new(fl.outputs[0], wn.inputs["W"])
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.06, 1, 1)
    L.new(tc.outputs["Object"], mp.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = grain; nz.inputs["Detail"].default_value = 8
    nz.inputs["Distortion"].default_value = 0.5; L.new(mp.outputs[0], nz.inputs["Vector"])
    mx = N.new("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"; mx.inputs[1].default_value = 0.5
    L.new(wn.outputs["Value"], mx.inputs[0]); L.new(nz.outputs["Fac"], mx.inputs[2])
    sb = N.new("ShaderNodeMath"); sb.operation = "SUBTRACT"; sb.inputs[1].default_value = 0.3; L.new(mx.outputs[0], sb.inputs[0])
    cl = N.new("ShaderNodeClamp"); L.new(sb.outputs[0], cl.inputs[0])
    rp = N.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = (*c1, 1); rp.color_ramp.elements[1].color = (*c2, 1)
    L.new(cl.outputs[0], rp.inputs[0])
    g = N.new("ShaderNodeMath"); g.operation = "LESS_THAN"; g.inputs[1].default_value = gap / board
    L.new(fr.outputs[0], g.inputs[0])
    gm = N.new("ShaderNodeMath"); gm.operation = "MULTIPLY_ADD"; gm.inputs[1].default_value = -0.7
    gm.inputs[2].default_value = 1.0; L.new(g.outputs[0], gm.inputs[0])
    mc = N.new("ShaderNodeVectorMath"); mc.operation = "SCALE"
    L.new(rp.outputs["Color"], mc.inputs[0]); L.new(gm.outputs[0], mc.inputs["Scale"])
    L.new(mc.outputs[0], p.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.08
    L.new(nz.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs[0], p.inputs["Normal"])
    return m


def emission(name, color, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; N.remove(N["Principled BSDF"])
    e = N.new("ShaderNodeEmission"); e.inputs["Color"].default_value = (*color, 1); e.inputs["Strength"].default_value = strength
    m.node_tree.links.new(e.outputs[0], N["Material Output"].inputs[0]); return m


MAT = {
    "boden": wood("Eiche Boden", (0.36, 0.23, 0.12), (0.62, 0.44, 0.26)),
    "eiche": wood("Eiche Möbel", (0.45, 0.30, 0.17), (0.66, 0.48, 0.30), board=0.6, gap=0.0005),
    "weiss": plain("Weiß matt", (0.85, 0.84, 0.81), 0.6),
    "wand": noisy("Wandputz", (0.84, 0.82, 0.78), (0.90, 0.89, 0.86), 3, 0.9, 0.05, 400),
    "stoff": noisy("Stoff beige", (0.55, 0.51, 0.44), (0.65, 0.61, 0.54), 40, 1.0, 0.25, 600),
    "stoff_gruen": noisy("Stoff salbei", (0.26, 0.31, 0.24), (0.33, 0.38, 0.30), 40, 1.0, 0.25, 600),
    "schwarz": plain("Metall schwarz", (0.03, 0.03, 0.03), 0.35, 0.6),
    "arbeitsplatte": noisy("Arbeitsplatte Stein", (0.10, 0.10, 0.10), (0.18, 0.18, 0.17), 30, 0.3, 0.02),
    "front": plain("Fronten greige", (0.62, 0.60, 0.55), 0.5),
    "edelstahl": noisy("Edelstahl", (0.55, 0.55, 0.55), (0.65, 0.65, 0.65), 200, 0.25, 0.02, 800, 1.0),
    "teppich": noisy("Wollteppich", (0.68, 0.64, 0.56), (0.78, 0.74, 0.66), 8, 1.0, 0.5, 900),
    "pflanze": noisy("Blätter", (0.05, 0.14, 0.04), (0.16, 0.30, 0.09), 25, 0.6, 0.8, 60),
    "topf": noisy("Terrakotta", (0.45, 0.22, 0.13), (0.58, 0.31, 0.19), 20, 0.8, 0.2),
    "licht": emission("Licht warm", (1.0, 0.80, 0.55), 12 if not DAYLIGHT else 4),
    "glas": plain("Glas", (1, 1, 1), 0.0, **{"Transmission Weight": 1.0, "Transmission": 1.0, "IOR": 1.5}),
    "rahmen": plain("Fensterrahmen weiß", (0.88, 0.88, 0.86), 0.4),
    "tuer": plain("Tür weiß", (0.86, 0.85, 0.82), 0.45),
}
PALETTE = {  # Farben aus der IFC-Datei -> Render-Material
    "eiche": (0.62, 0.45, 0.28), "weiss": (0.92, 0.91, 0.88), "wand": (0.93, 0.92, 0.89),
    "stoff": (0.66, 0.63, 0.56), "stoff_gruen": (0.32, 0.38, 0.30), "schwarz": (0.06, 0.06, 0.06),
    "arbeitsplatte": (0.20, 0.20, 0.20), "front": (0.78, 0.76, 0.70), "glas": (0.75, 0.85, 0.9),
    "edelstahl": (0.6, 0.6, 0.6), "teppich": (0.80, 0.76, 0.68), "pflanze": (0.15, 0.32, 0.12),
    "topf": (0.55, 0.35, 0.25), "licht": (1.0, 0.85, 0.6),
}


def nearest(rgb):
    if hasattr(rgb, "r") and callable(rgb.r):   # ifcopenshell >= 0.8 liefert ein colour-Objekt
        rgb = (rgb.r(), rgb.g(), rgb.b())
    return min(PALETTE, key=lambda k: sum((a - b) ** 2 for a, b in zip(PALETTE[k], rgb)))


# ---------------------------------------------------------------------------
# IFC laden
# ---------------------------------------------------------------------------
ifc = ifcopenshell.open(os.path.join(HERE, IFC_NAME))
st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)


def add_mesh(name, sh, override=None):
    g = sh.geometry; v, fc = g.verts, g.faces
    me = bpy.data.meshes.new(name)
    me.from_pydata([(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)], [],
                   [(fc[i], fc[i + 1], fc[i + 2]) for i in range(0, len(fc), 3)])
    keys = []
    mids = list(g.material_ids)
    for i, poly in enumerate(me.polygons):
        k = override or (nearest(g.materials[mids[i]].diffuse) if mids and mids[i] >= 0 else "weiss")
        if k not in keys:
            keys.append(k); me.materials.append(MAT[k])
        poly.material_index = keys.index(k)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    return ob


def cube(name, mtx, cx, cz, sx, sy, sz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name
    o.scale = (sx, sy, sz)
    o.matrix_world = mtx @ Matrix.Translation((cx, 0, cz)) @ o.matrix_basis
    o.data.materials.append(MAT[mat]); return o


def window_or_door(el):
    mtx = Matrix(ifcopenshell.util.placement.get_local_placement(el.ObjectPlacement).tolist())
    w, h, fr = el.OverallWidth, el.OverallHeight, 0.06
    if el.is_a("IfcDoor"):
        cube(el.Name + " Zarge L", mtx, fr / 2, h / 2, fr, 0.16, h, "rahmen")
        cube(el.Name + " Zarge R", mtx, w - fr / 2, h / 2, fr, 0.16, h, "rahmen")
        cube(el.Name + " Zarge O", mtx, w / 2, h - fr / 2, w, 0.16, fr, "rahmen")
        cube(el.Name + " Blatt", mtx, w / 2, (h - fr) / 2, w - 2 * fr, 0.04, h - fr, "tuer")
        return
    for (cx, cz, sx, sz) in [(w / 2, fr / 2, w, fr), (w / 2, h - fr / 2, w, fr), (fr / 2, h / 2, fr, h),
                             (w - fr / 2, h / 2, fr, h), (w / 2, h / 2, fr * 1.2, h)]:
        cube(el.Name + " Rahmen", mtx, cx, cz, sx, 0.08, sz, "rahmen")
    cube(el.Name + " Glas", mtx, w / 2, h / 2, w - fr, 0.02, h - fr, "glas")
    cube(el.Name + " Fensterbank", mtx, w / 2, -0.01, w + 0.1, 0.28, 0.02, "weiss")


OBJ = {}
for el in ifc.by_type("IfcProduct"):
    if el.is_a() in ("IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcOpeningElement", "IfcSpace") \
            or not el.Representation:
        continue
    if el.is_a("IfcWindow") or el.is_a("IfcDoor"):
        window_or_door(el); continue
    sh = ifcopenshell.geom.create_shape(st, el)
    override = "boden" if el.is_a("IfcSlab") and "Boden" in el.Name else None
    ob = add_mesh(el.Name, sh, override)
    OBJ[el.Name] = ob
    if el.is_a("IfcFurniture") and any(k in el.Name for k in ("Sofa", "Küche", "Sideboard", "Garderobe")):
        b = ob.modifiers.new("Kanten", "BEVEL"); b.width = 0.008; b.segments = 2
    if "Pflanze" in el.Name:   # Blätter etwas organischer
        sub = ob.modifiers.new("s", "SUBSURF"); sub.levels = 2; sub.render_levels = 2
        tex = bpy.data.textures.new("blatt", "CLOUDS"); tex.noise_scale = 0.08
        d = ob.modifiers.new("d", "DISPLACE"); d.texture = tex; d.strength = 0.12

# ---------------------------------------------------------------------------
# Außen: Gegenüberliegende Fassade + Himmel, Sonne
# ---------------------------------------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=200, location=(2, 0, -3.0))
bpy.context.object.data.materials.append(noisy("Straße", (0.22, 0.22, 0.22), (0.3, 0.3, 0.29), 4))
bpy.ops.mesh.primitive_cube_add(size=1, location=(2, 22, 6))
fa = bpy.context.object; fa.scale = (60, 1, 30)
fa.data.materials.append(noisy("Fassade gegenüber", (0.78, 0.72, 0.62), (0.86, 0.80, 0.70), 2, 0.9))

world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
sky = wn.new("ShaderNodeTexSky")
for t in ("MULTIPLE_SCATTERING", "NISHITA", "HOSEK_WILKIE"):
    try:
        sky.sky_type = t; break
    except TypeError:
        continue
for a, val in (("sun_elevation", math.radians(28 if DAYLIGHT else 3)), ("sun_rotation", math.radians(200))):
    if hasattr(sky, a):
        setattr(sky, a, val)
wl.new(sky.outputs[0], wn["Background"].inputs[0])
wn["Background"].inputs["Strength"].default_value = 0.4 if DAYLIGHT else 0.08

sun = bpy.data.lights.new("Sonne", "SUN"); sun.energy = 4.0 if DAYLIGHT else 0.0
sun.color = (1.0, 0.92, 0.82); sun.angle = math.radians(1.0)
so = bpy.data.objects.new("Sonne", sun); scene.collection.objects.link(so)
so.rotation_euler = (Vector((-0.35, -1.0, -0.55))).to_track_quat("-Z", "Y").to_euler()

# Fensterlicht (Portal-Licht hilft gegen Rauschen)
for x in (1.15, 2.85):
    ld = bpy.data.lights.new("Fensterlicht", "AREA"); ld.energy = 120 if DAYLIGHT else 5; ld.size = 1.2
    ld.shape = "RECTANGLE"; ld.size_y = 1.6; ld.color = (0.85, 0.9, 1.0)
    o = bpy.data.objects.new("Fensterlicht", ld); o.location = (x, 5.2, 1.65)
    o.rotation_euler = (math.radians(-90), 0, 0); scene.collection.objects.link(o)
for name, loc, e in (("Pendel", (2.2, 1.6, 1.6), 25), ("Stehlampe", (3.72, 2.72, 1.5), 30),
                     ("Küche LED", (0.45, 1.65, 1.40), 15)):
    ld = bpy.data.lights.new(name, "POINT"); ld.energy = e * (0.4 if DAYLIGHT else 1.5); ld.color = (1, 0.78, 0.55)
    o = bpy.data.objects.new(name, ld); o.location = loc; scene.collection.objects.link(o)

# ---------------------------------------------------------------------------
# Kameras + Render
# ---------------------------------------------------------------------------
def camera(name, loc, target, lens=14, ortho=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens
    if ortho:
        cd.type = "ORTHO"; cd.ortho_scale = ortho
    co = bpy.data.objects.new(name, cd); scene.collection.objects.link(co)
    co.location = loc; co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return co


CAMS = {
    "wohnen": camera("Ansicht Wohnen", (3.75, 0.35, 1.55), (0.9, 4.6, 1.05), 14),
    "kueche": camera("Ansicht Küche", (2.95, 5.05, 1.55), (0.3, 0.9, 1.05), 14),
    "draufsicht": camera("Draufsicht", (2.0, 2.625, 12), (2.0, 2.6251, 0), ortho=6.6),
}
CAMS["draufsicht"].rotation_euler = (0, 0, 0)   # Norden oben, Küche links

scene.render.engine = "CYCLES"
scene.cycles.samples = args.samples
scene.cycles.max_bounces = 10
scene.render.resolution_x = int(1080 * args.res); scene.render.resolution_y = int(1350 * args.res)
if not args.cpu:
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dev in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
            try:
                prefs.compute_device_type = dev; prefs.get_devices()
                if any(d.type == dev for d in prefs.devices):
                    for d in prefs.devices: d.use = True
                    scene.cycles.device = "GPU"; break
            except Exception:
                pass
    except Exception:
        pass
try:
    scene.cycles.use_denoising = True
except Exception:
    pass
try:
    scene.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
        try:
            scene.view_settings.look = look; break
        except TypeError:
            continue
except Exception:
    pass

views = list(CAMS) if args.view == "all" else [args.view]
for v in views:
    scene.camera = CAMS[v]
    top = v == "draufsicht"
    if "Decke" in OBJ:
        OBJ["Decke"].hide_render = top
    scene.view_settings.exposure = -0.3 if top else -0.5
    scene.render.filepath = os.path.join(args.out, f"{v}.png")
    try:
        bpy.ops.render.render(write_still=True)
    except RuntimeError as e:
        print("Ohne Denoiser:", e); scene.cycles.use_denoising = False
        bpy.ops.render.render(write_still=True)
    print("RENDERED", scene.render.filepath)
if "Decke" in OBJ:
    OBJ["Decke"].hide_render = False
