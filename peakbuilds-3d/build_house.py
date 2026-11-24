"""
peakBuilds – parametrisches Tiny House (Blender 4.x)

Baut ein modulares Holz-Tiny-House mit Satteldach, verglaster Giebelfront
und Schlafgalerie, setzt es in eine Alpen-/Waldlandschaft und rendert
eine Außen- und eine Innenansicht.

Aufruf:
    blender -b -P build_house.py -- --out renders/ --view both --samples 96
"""
import bpy, bmesh, math, random, sys, argparse, os
from mathutils import Vector

# ---------------------------------------------------------------------------
# Parameter (hier neue Häuser "konfigurieren")
# ---------------------------------------------------------------------------
CFG = dict(
    name="Forest Loft",
    width=4.4,          # Breite (m)
    length=8.0,         # Länge (m), 2 Module à 4 m
    wall_h=2.8,         # Traufhöhe
    ridge_h=5.2,        # Firsthöhe
    t=0.22,             # Wandstärke
    plinth=0.45,        # Haus steht auf Punktfundamenten
    gallery_depth=3.2,  # Tiefe der Galerie (hinten)
    gallery_z=2.45,     # Höhe Galerieboden über Erdgeschoss
    sun_elev=9.0,       # Sonnenhöhe in Grad (Golden Hour)
    sun_rot=-35.0,      # Sonnenrichtung
    seed=7,
)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="renders")
ap.add_argument("--view", default="both", choices=["exterior", "interior", "both"])
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", type=float, default=1.0)  # 1.0 = 1080x1350
args = ap.parse_args(argv)
os.makedirs(args.out, exist_ok=True)
random.seed(CFG["seed"])

W, L, h, H, t = CFG["width"], CFG["length"], CFG["wall_h"], CFG["ridge_h"], CFG["t"]
Z0 = CFG["plinth"]

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, color, rough=0.6, metal=0.0, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    for k, v in kw.items():
        p.inputs[k].default_value = v
    return m


def boards_mat(name, c1, c2, board=0.14, gap=0.006, rough=0.75, vertical=True, scale_noise=40):
    """Holzlatten: Streifen entlang x+y (vertikal) bzw. z (horizontal), je Brett andere Farbe."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, Ln = nt.nodes, nt.links
    p = N["Principled BSDF"]
    p.inputs["Roughness"].default_value = rough
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    Ln.new(tc.outputs["Object"], sep.inputs[0])
    u = N.new("ShaderNodeMath"); u.operation = "ADD"
    if vertical:
        Ln.new(sep.outputs[0], u.inputs[0]); Ln.new(sep.outputs[1], u.inputs[1])
    else:
        Ln.new(sep.outputs[2], u.inputs[0]); u.inputs[1].default_value = 0
    div = N.new("ShaderNodeMath"); div.operation = "DIVIDE"; div.inputs[1].default_value = board
    Ln.new(u.outputs[0], div.inputs[0])
    fl = N.new("ShaderNodeMath"); fl.operation = "FLOOR"; Ln.new(div.outputs[0], fl.inputs[0])
    fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"; Ln.new(div.outputs[0], fr.inputs[0])
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "1D"
    Ln.new(fl.outputs[0], wn.inputs["W"])
    # Maserung
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale_noise
    nz.inputs["Detail"].default_value = 6
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, 0.08) if vertical else (0.08, 0.08, 1)
    Ln.new(tc.outputs["Object"], mp.inputs[0]); Ln.new(mp.outputs[0], nz.inputs["Vector"])
    mixf = N.new("ShaderNodeMath"); mixf.operation = "MULTIPLY_ADD"
    Ln.new(wn.outputs["Value"], mixf.inputs[0]); mixf.inputs[1].default_value = 0.6
    Ln.new(nz.outputs["Fac"], mixf.inputs[2])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].color = (*c2, 1)
    clamp = N.new("ShaderNodeClamp")
    sub = N.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = 0.35
    Ln.new(mixf.outputs[0], sub.inputs[0]); Ln.new(sub.outputs[0], clamp.inputs[0])
    Ln.new(clamp.outputs[0], ramp.inputs[0])
    # Fugen dunkel
    g = N.new("ShaderNodeMath"); g.operation = "LESS_THAN"; g.inputs[1].default_value = gap / board
    Ln.new(fr.outputs[0], g.inputs[0])
    mixc = N.new("ShaderNodeMix"); mixc.data_type = "RGBA"
    Ln.new(g.outputs[0], mixc.inputs["Factor"])
    Ln.new(ramp.outputs["Color"], mixc.inputs[6])
    mixc.inputs[7].default_value = (0.05, 0.035, 0.025, 1)
    Ln.new(mixc.outputs[2], p.inputs["Base Color"])
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
    inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
    Ln.new(g.outputs[0], inv.inputs[1]); Ln.new(inv.outputs[0], bump.inputs["Height"])
    Ln.new(bump.outputs[0], p.inputs["Normal"])
    return m


def box(name, x0, x1, y0, y1, z0, z1, material=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.object
    o.name = name
    o.scale = ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL"); b.width = bevel; b.segments = 2
    if material:
        o.data.materials.append(material)
    return o


def prism(name, profile_xz, y0, y1, material=None):
    """Extrudiert ein Profil (Liste von (x,z)) entlang y."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in profile_xz]
    b = [bm.verts.new((x, y1, z)) for x, z in profile_xz]
    n = len(profile_xz)
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([a[i], a[j], b[j], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    if material:
        o.data.materials.append(material)
    return o


def boolean(target, cutter, mode="DIFFERENCE"):
    m = target.modifiers.new("b", "BOOLEAN")
    m.operation = mode
    m.object = cutter
    m.solver = "EXACT"
    try:
        m.material_mode = "TRANSFER"
    except Exception:
        pass
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def cyl(name, x, y, z0, z1, r, material=None, verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=z1 - z0, location=(x, y, (z0 + z1) / 2))
    o = bpy.context.object; o.name = name
    if material:
        o.data.materials.append(material)
    return o


# ---------------------------------------------------------------------------
# Materialien
# ---------------------------------------------------------------------------
M = dict(
    larch=boards_mat("larch", (0.34, 0.21, 0.11), (0.60, 0.41, 0.24)),
    ply=boards_mat("plywood", (0.78, 0.62, 0.44), (0.90, 0.78, 0.60), board=0.61, gap=0.004, rough=0.55, scale_noise=8),
    oak=boards_mat("oak", (0.55, 0.38, 0.22), (0.75, 0.56, 0.36), board=0.19, gap=0.003, rough=0.45, vertical=False),
    deck=boards_mat("deck", (0.38, 0.33, 0.28), (0.55, 0.48, 0.40), board=0.13, gap=0.012, rough=0.8),
    frame=mat("frame", (0.035, 0.035, 0.035), 0.4),
    roof=mat("roof", (0.07, 0.07, 0.075), 0.45, 0.6),
    glass=mat("glass", (0.95, 0.97, 0.97), 0.0, **{"Transmission Weight": 1.0, "IOR": 1.45}),
    concrete=mat("concrete", (0.35, 0.35, 0.34), 0.9),
    fabric=mat("fabric", (0.78, 0.74, 0.66), 0.95),
    fabric2=mat("fabric2", (0.30, 0.36, 0.30), 0.95),
    white=mat("white", (0.85, 0.84, 0.80), 0.5),
    counter=mat("counter", (0.12, 0.12, 0.12), 0.35),
    leaf=mat("leaf", (0.08, 0.22, 0.08), 0.7),
    pot=mat("pot", (0.55, 0.30, 0.20), 0.8),
    pine=mat("pine", (0.018, 0.05, 0.03), 0.85),
    bark=mat("bark", (0.16, 0.10, 0.07), 0.9),
    rock=mat("rock", (0.32, 0.31, 0.30), 0.9),
)
lamp = bpy.data.materials.new("lamp"); lamp.use_nodes = True
ln = lamp.node_tree.nodes; ln.remove(ln["Principled BSDF"])
em = ln.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (1.0, 0.72, 0.42, 1); em.inputs["Strength"].default_value = 12
lamp.node_tree.links.new(em.outputs[0], ln["Material Output"].inputs[0])
M["lamp"] = lamp

# Wiese
grass = bpy.data.materials.new("grass"); grass.use_nodes = True
gn, gl = grass.node_tree.nodes, grass.node_tree.links
gp = gn["Principled BSDF"]; gp.inputs["Roughness"].default_value = 0.95
gnz = gn.new("ShaderNodeTexNoise"); gnz.inputs["Scale"].default_value = 0.6; gnz.inputs["Detail"].default_value = 10
gr = gn.new("ShaderNodeValToRGB")
gr.color_ramp.elements[0].color = (0.035, 0.07, 0.02, 1)
gr.color_ramp.elements[1].color = (0.13, 0.17, 0.05, 1)
gl.new(gnz.outputs["Fac"], gr.inputs[0]); gl.new(gr.outputs[0], gp.inputs["Base Color"])
gnz2 = gn.new("ShaderNodeTexNoise"); gnz2.inputs["Scale"].default_value = 60
gb = gn.new("ShaderNodeBump"); gb.inputs["Strength"].default_value = 0.6
gl.new(gnz2.outputs["Fac"], gb.inputs["Height"]); gl.new(gb.outputs[0], gp.inputs["Normal"])

# ---------------------------------------------------------------------------
# Haus
# ---------------------------------------------------------------------------
outer = [(0, 0), (W, 0), (W, h), (W / 2, H), (0, h)]
shell = prism("shell", [(x, z + Z0) for x, z in outer], 0, L, M["larch"])

# Innenraum (Sperrholz-Oberflächen werden per Boolean übertragen)
a = math.atan2(H - h, W / 2)
dz_in = t / math.cos(a)
inner = [(t, 0), (W - t, 0), (W - t, h - t * math.tan(a) + 0.0), (W / 2, H - dz_in), (t, h - t * math.tan(a))]
cut_inner = prism("inner", [(x, z + Z0 + 0.0) for x, z in inner], t, L - t, M["ply"])
boolean(shell, cut_inner)

# Giebelfront komplett verglast (Rahmen 0.12 m)
f = 0.12
front = [(t + f - t, f), (W - f, f), (W - f, h - f * 0.2), (W / 2, H - f * 1.6), (f, h - f * 0.2)]
cut_front = prism("frontcut", [(x, z + Z0) for x, z in front], -0.5, t + 0.01, M["frame"])
boolean(shell, cut_front)

# Seitenfenster links (Wohnbereich) und hinten
cut_side = box("sidecut", -0.5, t + 0.01, 1.2, 3.6, Z0 + 0.85, Z0 + 2.15, M["frame"])
boolean(shell, cut_side)
cut_back = box("backcut", W / 2 - 0.6, W / 2 + 0.6, L - t - 0.01, L + 0.5, Z0 + CFG["gallery_z"] + 0.9, Z0 + CFG["gallery_z"] + 1.9, M["frame"])
boolean(shell, cut_back)

# Glas + Sprossen Front
glass_front = prism("glass_front", [(x, z + Z0) for x, z in front], 0.06, 0.075, M["glass"])
gz = Z0 + CFG["gallery_z"] + 0.1
box("transom", f, W - f, 0.04, 0.10, gz - 0.04, gz + 0.04, M["frame"])
box("mullion", W / 2 - 0.035, W / 2 + 0.035, 0.04, 0.10, Z0 + f, Z0 + H - f * 1.6, M["frame"])
box("mullion2", W * 0.25 - 0.03, W * 0.25 + 0.03, 0.04, 0.10, Z0 + f, gz, M["frame"])
box("glass_side", 0.05, 0.065, 1.2, 3.6, Z0 + 0.85, Z0 + 2.15, M["glass"])
box("glass_back", W / 2 - 0.6, W / 2 + 0.6, L - 0.08, L - 0.065, Z0 + CFG["gallery_z"] + 0.9, Z0 + CFG["gallery_z"] + 1.9, M["glass"])
# Fensterrahmen-Laibung außen (Akzent)
box("side_frame_top", -0.06, 0.02, 1.15, 3.65, Z0 + 2.15, Z0 + 2.21, M["frame"])

# Modulfuge (zwei Module sichtbar)
box("joint_l", -0.012, 0.0, L / 2 - 0.02, L / 2 + 0.02, Z0, Z0 + h, M["frame"])
box("joint_r", W, W + 0.012, L / 2 - 0.02, L / 2 + 0.02, Z0, Z0 + h, M["frame"])

# Dach
th, ov, ovy = 0.14, 0.45, 0.35
slope = math.hypot(W / 2, H - h) + ov
for side in (-1, 1):
    mx = W / 4 if side < 0 else 3 * W / 4
    mz = (h + H) / 2 + Z0
    d = Vector((W / 2, 0, H - h)).normalized()
    if side > 0:
        d = Vector((W / 2, 0, -(H - h))).normalized()
    nrm = Vector((-d.z, 0, d.x)) if side < 0 else Vector((d.z * -1, 0, d.x)) * -1
    nrm = Vector((-math.sin(a), 0, math.cos(a))) if side < 0 else Vector((math.sin(a), 0, math.cos(a)))
    eave_dir = -d if side < 0 else d
    c = Vector((mx, L / 2, mz)) + eave_dir * (ov / 2) + nrm * (th / 2 + 0.005)
    bpy.ops.mesh.primitive_cube_add(location=c)
    r = bpy.context.object; r.name = f"roof{side}"
    r.scale = (slope / 2, (L + 2 * ovy) / 2, th / 2)
    r.rotation_euler = (0, -a if side < 0 else a, 0)
    r.data.materials.append(M["roof"])

# Sockel / Punktfundamente
for x in (0.3, W - 0.3):
    for y in (0.4, L / 2, L - 0.4):
        box("pier", x - 0.15, x + 0.15, y - 0.15, y + 0.15, -0.2, Z0, M["concrete"])
box("skirt", 0.15, W - 0.15, 0.25, L - 0.25, 0.05, Z0 - 0.02, M["frame"])

# Terrasse + Stufe + Trittsteine
box("deck", -0.6, W + 0.6, -2.4, 0.0, Z0 - 0.08, Z0, M["deck"])
for x in (-0.4, W / 2, W + 0.4):
    box("deckpost", x - 0.06, x + 0.06, -2.3, -2.18, -0.2, Z0 - 0.08, M["concrete"])
box("step", W / 2 - 0.8, W / 2 + 0.8, -2.85, -2.4, Z0 / 2 - 0.04, Z0 / 2 + 0.02, M["deck"])
for i, (sx, sy) in enumerate([(2.0, -3.6), (1.6, -4.6), (2.1, -5.7), (1.5, -6.8)]):
    s = cyl("stone", sx, sy, -0.05, 0.03, 0.32 + 0.05 * (i % 2), M["rock"], 10)
    s.scale = (1.0, 0.75, 1)

# ---------------------------------------------------------------------------
# Innenausbau
# ---------------------------------------------------------------------------
gy0 = L - t - CFG["gallery_depth"]
G = Z0 + CFG["gallery_z"]
box("floor", t, W - t, t, L - t, Z0, Z0 + 0.02, M["oak"])
box("gallery", t, W - t, gy0, L - t, G - 0.2, G, M["ply"])
box("gallery_floor", t, W - t, gy0, L - t, G, G + 0.02, M["oak"])
# Glasgeländer + Handlauf
box("rail_glass", t, W - t - 0.9, gy0 - 0.02, gy0, G + 0.02, G + 1.0, M["glass"])
box("rail_top", t, W - t - 0.9, gy0 - 0.03, gy0 + 0.01, G + 1.0, G + 1.04, M["oak"])
# Treppe mit Stauraum (rechte Wand)
steps, sw = 11, 0.85
run = 2.6
for i in range(steps):
    y1 = gy0 - run + (i + 1) * run / steps
    box(f"stair{i}", W - t - sw, W - t, y1 - run / steps, y1, Z0, Z0 + (i + 1) * (G - Z0) / steps, M["ply"])
    box(f"tread{i}", W - t - sw, W - t, y1 - run / steps, y1 + 0.02, Z0 + (i + 1) * (G - Z0) / steps, Z0 + (i + 1) * (G - Z0) / steps + 0.03, M["oak"])
# Küche unter der Galerie (links)
box("kitchen", t, t + 0.62, gy0 + 0.1, L - t, Z0, Z0 + 0.88, M["white"], 0.005)
box("worktop", t, t + 0.64, gy0 + 0.1, L - t, Z0 + 0.88, Z0 + 0.92, M["counter"])
box("shelf", t, t + 0.3, gy0 + 0.4, L - t - 0.3, Z0 + 1.55, Z0 + 1.58, M["oak"])
box("strip", t + 0.25, t + 0.3, gy0 + 0.4, L - t - 0.3, G - 0.22, G - 0.2, M["lamp"])
# Bett auf der Galerie
box("mattress", W / 2 - 0.8, W / 2 + 0.8, L - t - 2.1, L - t - 0.1, G + 0.02, G + 0.25, M["fabric"], 0.04)
box("blanket", W / 2 - 0.82, W / 2 + 0.82, L - t - 1.5, L - t - 0.6, G + 0.25, G + 0.3, M["fabric2"], 0.03)
# Wohnbereich: Sofa, Teppich, Tisch, Pflanze, Pendelleuchte
sx0 = t + 0.1
box("sofa_base", sx0, sx0 + 0.9, 1.0, 3.2, Z0, Z0 + 0.42, M["fabric"], 0.04)
box("sofa_back", sx0, sx0 + 0.22, 1.0, 3.2, Z0 + 0.42, Z0 + 0.85, M["fabric"], 0.05)
box("sofa_arm1", sx0, sx0 + 0.9, 1.0, 1.2, Z0 + 0.42, Z0 + 0.62, M["fabric"], 0.05)
box("sofa_arm2", sx0, sx0 + 0.9, 3.0, 3.2, Z0 + 0.42, Z0 + 0.62, M["fabric"], 0.05)
box("cushion", sx0 + 0.25, sx0 + 0.4, 2.2, 2.6, Z0 + 0.42, Z0 + 0.75, M["fabric2"], 0.06)
box("rug", 1.0, 3.2, 1.0, 3.3, Z0 + 0.02, Z0 + 0.03, M["fabric2"])
cyl("table", 2.0, 2.1, Z0 + 0.02, Z0 + 0.42, 0.38, M["oak"], 32)
cyl("pot", W - t - 0.35, 0.6, Z0 + 0.02, Z0 + 0.45, 0.2, M["pot"])
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.42, location=(W - t - 0.35, 0.6, Z0 + 0.85))
bpy.context.object.data.materials.append(M["leaf"])
cyl("cable", W / 2, 2.2, Z0 + 2.3, Z0 + H - 0.3, 0.006, M["frame"], 8)
cyl("pendant", W / 2, 2.2, Z0 + 2.15, Z0 + 2.3, 0.16, M["frame"], 32)
cyl("bulb", W / 2, 2.2, Z0 + 2.13, Z0 + 2.16, 0.12, M["lamp"], 32)

# Innenlicht (warm)
def area(name, loc, size, energy, color=(1.0, 0.75, 0.5)):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.size = size; ld.color = color
    o = bpy.data.objects.new(name, ld); o.location = loc; scene.collection.objects.link(o)
    return o

area("in1", (W / 2, 2.2, Z0 + 2.05), 0.3, 45)
area("in2", (W / 2, gy0 + 1.5, G - 0.25), 1.2, 35)
area("in3", (W / 2, L - 1.5, Z0 + H - 0.6), 1.0, 30)
pl = bpy.data.lights.new("fill", "POINT"); pl.energy = 20; pl.color = (1, 0.8, 0.6)
po = bpy.data.objects.new("fill", pl); po.location = (W / 2, 3.5, Z0 + 1.6); scene.collection.objects.link(po)

# ---------------------------------------------------------------------------
# Landschaft
# ---------------------------------------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, 0))
ground = bpy.context.object; ground.data.materials.append(grass)


def pine(x, y, hgt):
    cyl("trunk", x, y, 0, hgt * 0.35, hgt * 0.025, M["bark"], 8)
    tiers = 8
    for i in range(tiers):
        r = hgt * (0.15 - i * 0.016) * random.uniform(0.85, 1.1)
        z0 = hgt * (0.16 + i * 0.095)
        bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=r, radius2=0, depth=hgt * 0.24, location=(x, y, z0 + hgt * 0.12))
        c = bpy.context.object; c.data.materials.append(M["pine"])
        c.rotation_euler.z = random.random() * 6.28


for _ in range(170):
    ang = random.uniform(0, 2 * math.pi)
    dist = random.uniform(11, 80)
    x, y = W / 2 + math.cos(ang) * dist, L / 2 + math.sin(ang) * dist
    # Sichtachse vorne-links freihalten
    if y < 4 and -22 < x < 16:
        continue
    pine(x, y, random.uniform(9, 19))

# Berge im Hintergrund
haze = mat("haze", (0.42, 0.48, 0.55), 1.0)
for (mx, my, r, hh) in [(-160, 420, 260, 210), (60, 480, 230, 260), (260, 430, 240, 190), (-420, 300, 220, 160)]:
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=r, depth=hh, location=(mx, my, hh / 2 - 10))
    m_ = bpy.context.object; m_.data.materials.append(haze)
    sub = m_.modifiers.new("s", "SUBSURF"); sub.levels = 3; sub.render_levels = 3; sub.subdivision_type = "SIMPLE"
    tex = bpy.data.textures.new("mt", "CLOUDS"); tex.noise_scale = 60
    dis = m_.modifiers.new("d", "DISPLACE"); dis.texture = tex; dis.strength = 45

# ---------------------------------------------------------------------------
# Himmel, Sonne, Render
# ---------------------------------------------------------------------------
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
wn = world.node_tree.nodes
sky = wn.new("ShaderNodeTexSky"); sky.sky_type = "NISHITA"
sky.sun_elevation = math.radians(CFG["sun_elev"]); sky.sun_rotation = math.radians(CFG["sun_rot"])
sky.air_density = 1.2; sky.dust_density = 2.5
wn["Background"].inputs["Strength"].default_value = 0.22
world.node_tree.links.new(sky.outputs[0], wn["Background"].inputs[0])
sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 3.6; sun.color = (1.0, 0.66, 0.40); sun.angle = math.radians(1.5)
so = bpy.data.objects.new("sun", sun); scene.collection.objects.link(so)
to_sun = Vector((-0.62, -0.78, math.tan(math.radians(CFG["sun_elev"])))).normalized()
so.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
sky.sun_rotation = math.atan2(to_sun.x, to_sun.y) * -1 + math.pi / 2

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = args.samples
scene.cycles.use_denoising = False
scene.cycles.max_bounces = 6
scene.render.resolution_x = int(1080 * args.res)
scene.render.resolution_y = int(1350 * args.res)
scene.render.image_settings.file_format = "PNG"
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
scene.view_settings.exposure = 0.2


def camera(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens
    co = bpy.data.objects.new(name, cd); scene.collection.objects.link(co)
    co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return co


views = []
if args.view in ("exterior", "both"):
    views.append(("exterior", camera("cam_ext", (-5.2, -7.6, 1.55), (W / 2 + 0.2, L / 2 - 0.8, Z0 + 2.3), 26)))
if args.view in ("interior", "both"):
    views.append(("interior", camera("cam_int", (W - t - 1.2, 0.45, Z0 + 1.35), (W / 2 - 0.6, L - 1.2, Z0 + 2.3), 16)))

for vname, cam in views:
    scene.camera = cam
    scene.view_settings.exposure = 0.1 if vname == "exterior" else -0.6
    scene.render.filepath = os.path.join(args.out, f"{vname}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", scene.render.filepath)
