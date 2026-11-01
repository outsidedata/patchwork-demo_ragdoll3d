# The block of TNT: sixteen sticks of dynamite stood on end, four by four, packed into a cube `size`
# metres on a side, bound by two black straps with a buckle each, a paper label on every side carrying
# the letters TNT raised in black, and a detonator on top, its two wires running down into the middle
# sticks. Every colour is plain, no maps. This script is the model's source, which the game's bake runs
# (`demo_ragdoll3d.bake.ts`) with the block's `size` read off its definition (`tnt` in
# `demo_ragdoll3d.json`):
#
#   /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
#       --python games/demo_ragdoll3d/assets/tnt.py -- <out.glb> <size> [<preview dir>]
#
# It is built in Blender's frame, +Z up, the origin the middle of the block's bottom face, so the glb
# stands on the row's `pos` as the rule's block does (`tnt.sim.ts`); the glTF exporter turns +Z into
# three's +Y. Nothing reaches past the cube but the detonator on top, so a shot that meets the cube
# (`player.sim.ts`) meets what is drawn. It joins its parts into one mesh, prints its triangles and
# bounds, writes the glb, and with a preview folder renders it from four sides.
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
SIZE = float(argv[1])
PREVIEW = argv[2] if len(argv) > 2 else None

bpy.ops.wm.read_factory_settings(use_empty=True)

N = 4                          # sticks a side
R = SIZE / N / 2               # a stick's radius
CRIMP = R * 0.55               # how far a stick's crimped end falls in from its rim
END = SIZE * 0.045             # how tall the crimp is
STRAP = (0.2, 0.8)             # each strap's height, a share of the block's
STRAP_TALL = SIZE * 0.07
STRAP_OUT = SIZE * 0.012       # how far a strap stands off the sticks' outer faces
LABEL = (0.36, 0.64)           # the label's foot and head, shares of the block's height
LABEL_OUT = SIZE * 0.008


def material(name, col, rough, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*[((col >> s) & 255) / 255 for s in (16, 8, 0)], 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


PAPER = material('paper', 0xb8261c, 0.62)        # the sticks' red paper
CRIMPED = material('crimped', 0xd9c7a0, 0.8)     # their folded ends
STRAPS = material('strap', 0x18181a, 0.55)
BUCKLE = material('buckle', 0x8a8c90, 0.35, 1.0)
LABELS = material('label', 0xeee6d2, 0.75)
INK = material('ink', 0x141414, 0.6)
CASE = material('case', 0x2b2d31, 0.45, 0.3)     # the detonator's box
REDWIRE = material('redwire', 0xc0201a, 0.5)
BLACKWIRE = material('blackwire', 0x101010, 0.5)
BRASS = material('brass', 0xc8a050, 0.3, 1.0)

parts = []


def finish(ob, mat, bevel=0.0, segments=2):
    ob.data.materials.append(mat)
    if bevel:
        mod = ob.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(40)
    parts.append(ob)
    return ob


def mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def lathe(name, mat, profile, at, sides=32, bevel=0.0):
    """A solid of revolution about the vertical through `at` (x, y): `profile` is (radius, z) points from
    the bottom's middle up its side to the top's middle."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append([bm.verts.new((at[0], at[1], z))])
            continue
        rings.append([bm.verts.new((at[0] + r * math.cos(2 * math.pi * k / sides), at[1] + r * math.sin(2 * math.pi * k / sides), z))
                      for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1:
            for k in range(sides):
                bm.faces.new((a[0], b[(k + 1) % sides], b[k]))
        elif len(b) == 1:
            for k in range(sides):
                bm.faces.new((a[k], a[(k + 1) % sides], b[0]))
        else:
            for k in range(sides):
                j = (k + 1) % sides
                bm.faces.new((a[k], a[j], b[j], b[k]))
    return finish(mesh_object(name, bm), mat, bevel)


def box(name, mat, lo, hi, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, verts=bm.verts, vec=[hi[i] - lo[i] for i in range(3)])
    bmesh.ops.translate(bm, verts=bm.verts, vec=[(hi[i] + lo[i]) / 2 for i in range(3)])
    return finish(mesh_object(name, bm), mat, bevel)


def band(name, mat, z0, z1, half, corner, out, sides=8):
    """A strap round the bundle: a rounded square ring, `half` metres from the middle to its inner faces,
    its corners rounded by `corner`, `out` thick, from z0 up to z1."""
    bm = bmesh.new()

    def ring(h, z):
        pts = []
        for cx, cy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
            for s in range(sides + 1):
                a = math.radians(a0 + 90 * s / sides)
                pts.append(bm.verts.new((cx * (h - corner) + corner * math.cos(a), cy * (h - corner) + corner * math.sin(a), z)))
        return pts
    inner0, inner1 = ring(half, z0), ring(half, z1)
    corner += out
    outer0, outer1 = ring(half + out, z0), ring(half + out, z1)
    n = len(inner0)
    for a, b, flip in ((inner0, inner1, True), (outer0, outer1, False), (outer0, inner0, True), (outer1, inner1, False)):
        for k in range(n):
            j = (k + 1) % n
            q = (a[k], a[j], b[j], b[k])
            bm.faces.new(tuple(reversed(q)) if flip else q)
    return finish(mesh_object(name, bm), mat, 0.0)


def word(name, mat, text, size, depth, at, facing):
    """`text` in Blender's own font, `size` metres tall, raised `depth` off a face, its middle at `at`,
    read from outside a face whose outward normal is `facing` (an angle about +Z, 0 for +Y)."""
    bpy.ops.object.text_add()
    ob = bpy.context.active_object
    ob.name = name
    ob.data.body = text
    ob.data.size = size
    ob.data.extrude = depth / 2
    ob.data.align_x = 'CENTER'
    ob.data.align_y = 'CENTER'
    ob.data.space_character = 1.05
    bpy.ops.object.convert(target='MESH')
    ob = bpy.context.active_object
    # Lying face up (+Z) as Blender makes it: stood up to face +Y, then raised its half depth off the face.
    ob.data.transform(Matrix.Rotation(math.pi / 2, 4, 'X'))
    ob.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    ob.data.transform(Matrix.Translation((0, depth / 2, 0)))
    ob.data.transform(Matrix.Rotation(facing, 4, 'Z'))
    ob.data.transform(Matrix.Translation(at))
    ob.location = (0, 0, 0)
    ob.select_set(False)
    return finish(ob, mat, 0.0)


def wire(name, mat, pts, r):
    """A wire through `pts`, a poly curve given thickness `r`."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('NURBS')
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*q, 1)
    sp.use_endpoint_u = True
    sp.order_u = 3
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    cu.resolution_u = 12
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target='MESH')
    ob = bpy.context.active_object
    ob.select_set(False)
    return finish(ob, mat)


# The sticks: each a paper tube a hair inside its cell, its two ends folded in and crimped flat.
inset = R * 0.985
for i in range(N):
    for j in range(N):
        cx, cy = (i + 0.5) * 2 * R - SIZE / 2, (j + 0.5) * 2 * R - SIZE / 2
        lathe(f'stick{i}{j}', PAPER, [(0, END * 0.4), (CRIMP, END * 0.4), (inset * 0.9, END * 0.8), (inset, END),
                                      (inset, SIZE - END), (inset * 0.9, SIZE - END * 0.8), (CRIMP, SIZE - END * 0.4),
                                      (0, SIZE - END * 0.4)], (cx, cy))
        lathe(f'crimpbot{i}{j}', CRIMPED, [(0, 0.0), (CRIMP * 0.95, 0.0), (CRIMP, END * 0.42), (0, END * 0.42)], (cx, cy), sides=24)
        lathe(f'crimptop{i}{j}', CRIMPED, [(0, SIZE - END * 0.42), (CRIMP, SIZE - END * 0.42), (CRIMP * 0.95, SIZE), (0, SIZE)], (cx, cy), sides=24)

# The straps round the bundle, each with a steel buckle on its front.
for k, share in enumerate(STRAP):
    z = SIZE * share
    band(f'strap{k}', STRAPS, z - STRAP_TALL / 2, z + STRAP_TALL / 2, SIZE / 2 - R * 0.06, R * 0.95, STRAP_OUT)
    box(f'buckle{k}', BUCKLE, (-SIZE * 0.06, -SIZE / 2 - STRAP_OUT - SIZE * 0.012, z - STRAP_TALL * 0.62),
        (SIZE * 0.06, -SIZE / 2 - STRAP_OUT + 0.001, z + STRAP_TALL * 0.62), bevel=SIZE * 0.004)
    box(f'tongue{k}', BUCKLE, (-SIZE * 0.012, -SIZE / 2 - STRAP_OUT - SIZE * 0.016, z - STRAP_TALL * 0.3),
        (SIZE * 0.012, -SIZE / 2 - STRAP_OUT - SIZE * 0.008, z + STRAP_TALL * 0.3), bevel=SIZE * 0.002)

# The label on each side, wrapped over the sticks between the straps, and TNT raised on it.
z0, z1 = SIZE * LABEL[0], SIZE * LABEL[1]
half = SIZE / 2 - R * 0.06
band('label', LABELS, z0, z1, half, R * 0.95, LABEL_OUT)
for k in range(4):
    a = math.pi / 2 * k
    d = half + LABEL_OUT
    word(f'tnt{k}', INK, 'TNT', (z1 - z0) * 0.62, SIZE * 0.012,
         (-math.sin(a) * d, math.cos(a) * d, (z0 + z1) / 2 - (z1 - z0) * 0.05), a)

# The detonator on top: a box with two brass posts, its wires running down into the middle sticks.
top = SIZE
dw, dd, dh = SIZE * 0.26, SIZE * 0.16, SIZE * 0.1
box('detonator', CASE, (-dw / 2, -dd / 2, top), (dw / 2, dd / 2, top + dh), bevel=SIZE * 0.008)
box('dial', BUCKLE, (-dw * 0.18, -dd / 2 - 0.002, top + dh * 0.3), (dw * 0.18, -dd / 2 + 0.002, top + dh * 0.75), bevel=0.002)
for side, mat in ((-1, REDWIRE), (1, BLACKWIRE)):
    px = side * dw * 0.3
    lathe(f'post{side}', BRASS, [(0, top + dh - 0.002), (SIZE * 0.014, top + dh - 0.002), (SIZE * 0.014, top + dh + SIZE * 0.03),
                                 (SIZE * 0.02, top + dh + SIZE * 0.032), (SIZE * 0.02, top + dh + SIZE * 0.045), (0, top + dh + SIZE * 0.045)],
          (px, 0), sides=16)
    cell = side * R                     # the middle stick on that side
    wire(f'wire{side}', mat, [(px, 0, top + dh + SIZE * 0.035), (px + side * SIZE * 0.05, -SIZE * 0.02, top + dh + SIZE * 0.06),
                              (cell + side * SIZE * 0.04, -SIZE * 0.06, top + SIZE * 0.05), (cell, -R, top + SIZE * 0.02),
                              (cell, -R, top - END * 0.2)], SIZE * 0.007)

# Joined, measured, written.
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.convert(target='MESH')
bpy.ops.object.join()
block = bpy.context.active_object
block.name = 'tnt'
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
dg = bpy.context.evaluated_depsgraph_get()
ev = block.evaluated_get(dg).to_mesh()
ev.calc_loop_triangles()
xs, ys, zs = ([v.co[i] for v in ev.vertices] for i in range(3))
print(f'TRIS tnt={len(ev.loop_triangles)}')
print(f'BOUNDS x={min(xs):.3f}..{max(xs):.3f} y={min(ys):.3f}..{max(ys):.3f} z={min(zs):.3f}..{max(zs):.3f}')
block.evaluated_get(dg).to_mesh_clear()
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_yup=True, export_apply=True, export_animations=False)
print(f'tnt: wrote {OUT}')

if PREVIEW:
    os.makedirs(PREVIEW, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 1200, 900
    sc.view_settings.view_transform = 'Standard'
    sc.world = bpy.data.worlds.new('w')
    sc.world.use_nodes = True
    sc.world.node_tree.nodes['Background'].inputs[0].default_value = (0.42, 0.46, 0.52, 1)
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = 0.8
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    mid = Vector((0, 0, SIZE * 0.55))
    for a in (20, 110, 200, 290):
        t = math.radians(a)
        cam.location = mid + Vector((math.cos(t), math.sin(t), 0.45)) * SIZE * 3.2
        cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREVIEW, f'tnt-{a}.png')
        bpy.ops.render.render(write_still=True)
