# A stick of dynamite: a red paper tube `length` metres long and `radius` round, its ends folded in and
# crimped, a cream paper band round its middle with a thin black rule at either edge, and a brass ferrule
# at its fuse end where the fuse goes in. Every colour is plain, no maps. The fuse itself is not here: the
# stick's look draws it, burning shorter as its row says (`dynamite.client.ts`). This script is the
# model's source, which the game's bake runs (`demo_ragdoll3d.bake.ts`) with the stick's `radius` and
# `length` read off its box3d body (`world.box3d.kinds.dynamite` in `blast.scene.json`), so what is drawn
# is what box3d moves:
#
#   /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
#       --python games/demo_ragdoll3d/assets/dynamite.py -- <out.glb> <radius> <length> <root> [<preview dir>]
#
# `root` is the stick's definition's `fuse.root` (`dynamite` in `demo_ragdoll3d.json`): the ferrule stands
# that far past the end, and the look's fuse starts at its tip.
#
# Built in Blender's frame with the stick along +Z and its middle at the origin, the fuse end at +Z; the
# glTF exporter turns +Z into three's +Y, the axis box3d's cylinder stands along. It writes the glb, prints
# its triangles and bounds, and with a preview folder renders it.
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
R = float(argv[1])
L = float(argv[2])
ROOT = float(argv[3])   # how far the ferrule stands past the end, where the fuse starts
PREVIEW = argv[4] if len(argv) > 4 else None

bpy.ops.wm.read_factory_settings(use_empty=True)

CRIMP = R * 0.5      # the crimped end's radius
FOLD = R * 0.6       # how far the fold runs back from each end
BAND = L * 0.34      # the band's height
RULE = L * 0.012     # each black rule's height
SIDES = 40


def material(name, col, rough, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*[((col >> s) & 255) / 255 for s in (16, 8, 0)], 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


PAPER = material('paper', 0xb8261c, 0.6)
CRIMPED = material('crimped', 0xd9c7a0, 0.8)
CREAM = material('band', 0xeee6d2, 0.7)
INK = material('ink', 0x141414, 0.6)
BRASS = material('brass', 0xc8a050, 0.3, 1.0)

parts = []


def lathe(name, mat, profile, sides=SIDES):
    """A solid of revolution about +Z: `profile` is (radius, z) points from one end's middle round to
    the other's."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), z)) for k in range(sides)])
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
    me = bpy.data.meshes.new(name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    parts.append(ob)
    return ob


h = L / 2
# The paper tube, its ends folded in toward the crimps.
lathe('tube', PAPER, [(0, -h + FOLD * 0.2), (CRIMP, -h + FOLD * 0.2), (R * 0.88, -h + FOLD * 0.75), (R, -h + FOLD),
                      (R, h - FOLD), (R * 0.88, h - FOLD * 0.75), (CRIMP, h - FOLD * 0.2), (0, h - FOLD * 0.2)])
# The crimps, cream, a little proud of the folds.
lathe('crimpbot', CRIMPED, [(0, -h), (CRIMP * 0.9, -h), (CRIMP * 1.02, -h + FOLD * 0.3), (0, -h + FOLD * 0.3)])
lathe('crimptop', CRIMPED, [(0, h - FOLD * 0.3), (CRIMP * 1.02, h - FOLD * 0.3), (CRIMP * 0.9, h), (0, h)])
# The band round the middle and its two rules, each standing a little off the paper.
lathe('band', CREAM, [(0, -BAND / 2), (R * 1.012, -BAND / 2), (R * 1.012, BAND / 2), (0, BAND / 2)])
for s in (-1, 1):
    z = s * (BAND / 2 - RULE * 1.5)
    lathe(f'rule{s}', INK, [(0, z - RULE / 2), (R * 1.02, z - RULE / 2), (R * 1.02, z + RULE / 2), (0, z + RULE / 2)])
# The ferrule the fuse goes into, at the fuse end's middle.
lathe('ferrule', BRASS, [(0, h - 0.002), (R * 0.22, h - 0.002), (R * 0.22, h + ROOT * 0.75), (R * 0.15, h + ROOT), (0, h + ROOT)], sides=16)

bpy.ops.object.select_all(action='DESELECT')
for ob in parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
stick = bpy.context.active_object
stick.name = 'dynamite'
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
me = stick.data
me.calc_loop_triangles()
zs = [v.co.z for v in me.vertices]
xs = [v.co.x for v in me.vertices]
print(f'TRIS dynamite={len(me.loop_triangles)}')
print(f'BOUNDS radius={max(xs):.4f} z={min(zs):.4f}..{max(zs):.4f}')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_yup=True, export_apply=True, export_animations=False)
print(f'dynamite: wrote {OUT}')

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
    cam.location = Vector((L * 1.4, -L * 1.0, L * 0.6))
    cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(PREVIEW, 'dynamite.png')
    bpy.ops.render.render(write_still=True)
