# The shotgun: a pump-action in the manner of a Remington 870 Wingmaster with a short barrel, blued steel
# and varnished walnut. A rounded receiver with its ejection port and the bolt in it, a hollow barrel
# under a vent rib with a brass bead, the magazine tube and its cap, the barrel hanger, the action bars
# running back from a ribbed ("corncob") forend, a swept trigger guard round a curved trigger, the
# safety, and a walnut stock with a pistol grip, a white spacer and a ribbed rubber butt pad. This script
# is the model's source, which the game's bake runs (`demo_ragdoll3d.bake.ts`):
#
#   /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
#       --python games/demo_ragdoll3d/assets/shotgun.py -- <out.glb> \
#       <wood colour> <wood roughness> <wood normal> <steel colour> <steel roughness> <steel normal> \
#       [<preview dir>]
#
# The six maps are the wood's and the steel's (cc0-textures sets, cut small by the bake). The wood's
# colour is darkened toward walnut by `WOOD_TINT` and the steel's toward blued black by `BLUED_TINT`, in
# the pixels, so the glb carries the colours as drawn; the bolt and the trigger keep the steel bright,
# `BRIGHT_TINT`. Every part takes its UVs from a box projection whose u runs along the gun (+Y), so the
# wood's grain and the steel's brushing both run from butt to muzzle; `WOOD_TILE` and `STEEL_TILE` are
# the metres one repeat of each map covers. The wood has a clear varnish coat (`COAT`), which three draws
# as a clearcoat.
#
# It is built in one frame: Blender's +Z up, +Y toward the muzzle, +X the gun's right, the origin the
# middle of the pistol grip, where the right hand holds; the glTF exporter's Y-up conversion turns +Y
# into three's −Z. A part is an extruded side profile (rounded by a bevel and narrowed along the gun by
# a width function), a turned tube, a loft through cross sections, a strip swept along a side curve, or a
# box. `build` joins them, prints the gun's asserts and throws when one fails (triangles, length, where
# the muzzle is), writes the glb, and, given a preview folder, renders the gun from four sides, square on
# from each side, and close on the receiver.
#
# Its empties, which a body holds it by: `muzzle` at the barrel's mouth, where a round leaves; `stock` at
# the butt, the point set in the shoulder; `grip` on the pistol grip and `support` under the pump, where
# the right and left hands hold it, each turned as its hand holds, `SUPPORT` forward of the hold; and
# `eye` on the line over the rib and the bead, `SIGHT` high, `EYE` metres behind the hold, so whatever
# raises the gun to the eye puts that empty at the eye.
import bpy
import bmesh
import math
import os
import sys
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0]
WOOD_MAPS = argv[1:4]
STEEL_MAPS = argv[4:7]
PREVIEW = argv[7] if len(argv) > 7 else None

bpy.ops.wm.read_factory_settings(use_empty=True)

# The right hand on the grip, and the shoulder's point on the stock (Blender's frame).
GRIP = (0.0858, -0.1004, -0.0068)
GRIP_TURN = (0.598652, -0.365629, -0.618676, -0.353795)
STOCK = (0, -0.294, 0.0029)
SUPPORT_TURN = (0.640616, -0.28447, 0.122356, -0.70265)
# A hand under a fore-end of radius 0.026 holds it this far under its axis; one of another radius,
# nearer or farther by the difference.
UNDER = 0.129

BORE = 0.09       # the bore line's height over the hold
MUZZLE = 0.62     # the barrel's mouth, forward of the hold
BARREL = 0.0125   # the barrel's radius
TUBE = BORE - 0.027  # the magazine tube's axis, under the barrel
PUMP = 0.024      # the forend's radius about its axis, which the left hand's place is reckoned from
PUMP_AT = 0.066   # the forend's axis, between the barrel and the tube
SUPPORT = 0.30    # the left hand on the forend, forward of the hold
SIGHT = 0.1105    # the sight line, over the rib and the bead
EYE = -0.2        # the eye on the sight line, forward of the hold
BUTT = -0.294     # the butt pad's face, the gun's rear

RECEIVER = (-0.056, 0.16)  # the receiver from its rear to its face
TRIGGER = 0.064            # the trigger's foot, forward of the hold
FOREND = (0.205, 0.395)    # the forend from its rear to its front

WOOD_TINT = (0.62, 0.36, 0.25)
BLUED_TINT = (0.3, 0.33, 0.4)
BRIGHT_TINT = (0.78, 0.78, 0.8)
WOOD_TILE = 0.32
STEEL_TILE = 0.22
COAT = 0.07   # the varnish's roughness


# ---------- materials ----------

def image(path, name, tint=None, remap=None, colour=True):
    """A map, as a packed image of its own: its colour multiplied by `tint`, or its value taken to
    `remap` (lo, hi) of the way from black to white."""
    src = bpy.data.images.load(path)
    w, h = src.size
    px = np.empty(w * h * 4, dtype=np.float32)
    src.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    if tint:
        px[:, :3] *= np.array(tint, dtype=np.float32)
    if remap:
        px[:, :3] = remap[0] + px[:, :3] * (remap[1] - remap[0])
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
    img.pixels.foreach_set(px.ravel())
    img.pack()
    bpy.data.images.remove(src)
    return img


def textured(name, maps, metal, tint, remap, coat=None):
    """A material of a set's three maps: colour (tinted), roughness (remapped) and normal."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    b = nodes['Principled BSDF']
    col = nodes.new('ShaderNodeTexImage')
    col.image = image(maps[0], f'{name}_color', tint=tint)
    rough = nodes.new('ShaderNodeTexImage')
    rough.image = image(maps[1], f'{name}_rough', remap=remap, colour=False)
    nor = nodes.new('ShaderNodeTexImage')
    nor.image = image(maps[2], f'{name}_normal', colour=False)
    nmap = nodes.new('ShaderNodeNormalMap')
    links.new(col.outputs['Color'], b.inputs['Base Color'])
    links.new(rough.outputs['Color'], b.inputs['Roughness'])
    links.new(nor.outputs['Color'], nmap.inputs['Color'])
    links.new(nmap.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Metallic'].default_value = metal
    if coat is not None:
        b.inputs['Coat Weight'].default_value = 1.0
        b.inputs['Coat Roughness'].default_value = coat
    return m


def plain(name, col, rough, metal):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*[((col >> s) & 255) / 255 for s in (16, 8, 0)], 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


WALNUT = textured('walnut', WOOD_MAPS, 0.0, WOOD_TINT, (0.45, 0.75), coat=COAT)
BLUED = textured('blued', STEEL_MAPS, 1.0, BLUED_TINT, (0.24, 0.42))
BRIGHT = textured('bright', STEEL_MAPS, 1.0, BRIGHT_TINT, (0.18, 0.4))
DARK = plain('dark', 0x050506, 0.6, 0.4)         # the bore, the inside of the ports
RUBBER = plain('rubber', 0x141414, 0.9, 0.0)
SPACER = plain('spacer', 0xe8e4d8, 0.45, 0.0)    # the white line between the stock and the pad
BRASS = plain('brass', 0xc8a050, 0.3, 1.0)

TILE = {WALNUT.name: WOOD_TILE, BLUED.name: STEEL_TILE, BRIGHT.name: STEEL_TILE}

parts = []


# ---------- parts ----------

def uv_box(ob, tile):
    """UVs by a box projection in the world, u along +Y wherever a face allows it: a face facing ±X is
    (y, z), facing ±Z (y, x), facing ±Y (x, z); `tile` metres to a repeat."""
    me = ob.data
    uv = me.uv_layers.new(name='UVMap')
    mw = ob.matrix_world
    for poly in me.polygons:
        n = (mw.to_3x3() @ poly.normal)
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            p = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                u, v = p.y, p.z
            elif ax == 2:
                u, v = p.y, p.x
            else:
                u, v = p.x, p.z
            uv.data[li].uv = (u / tile, v / tile)


def finish(ob, mat, bevel=0.0015, segments=1, angle=30):
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if not ob.data.uv_layers:
        uv_box(ob, TILE.get(mat.name, 0.2))
    if bevel:
        mod = ob.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(angle)
        mod.harden_normals = segments == 1
    ob.select_set(False)
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


def profile(name, mat, pts, width, x=0.0, bevel=0.0015, segments=1, widths=None):
    """A side profile, (y, z) points round its outline seen from +X, extruded `width` across X about `x`;
    with `widths(y, z)`, each point's width there instead."""
    bm = bmesh.new()
    w = [widths(y, z) if widths else width for y, z in pts]
    left = [bm.verts.new((x - wi / 2, y, z)) for wi, (y, z) in zip(w, pts)]
    right = [bm.verts.new((x + wi / 2, y, z)) for wi, (y, z) in zip(w, pts)]
    bm.faces.new(list(reversed(left)))
    bm.faces.new(right)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((left[i], left[j], right[j], right[i]))
    return finish(mesh_object(name, bm), mat, bevel, segments)


def tube(name, mat, r, y0, y1, z, x=0.0, sides=24, bevel=0.0, hollow=0.0, depth=0.0):
    """A cylinder along +Y from y0 to y1, its axis at height z; with `hollow`, its front end bored
    `depth` deep, leaving a wall `hollow` thick."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r, radius2=r, depth=y1 - y0)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__('mathutils').Matrix.Rotation(-math.pi / 2, 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x, (y0 + y1) / 2, z))
    if hollow:
        front = max(bm.faces, key=lambda f: f.calc_center_median().y)
        inset = bmesh.ops.inset_individual(bm, faces=[front], thickness=hollow)
        bmesh.ops.translate(bm, verts=list(front.verts), vec=(0, -depth, 0))
    return finish(mesh_object(name, bm), mat, bevel)


def loft(name, mat, stations, n=32, bevel=0.0):
    """Cross sections along +Y, each (y, cx, cz, rx, rz, p): a superellipse of half-widths rx and rz and
    power p round (cx, cz), bridged one to the next and capped at both ends."""
    bm = bmesh.new()
    rings = []
    for y, cx, cz, rx, rz, p in stations:
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            c, s = math.cos(a), math.sin(a)
            ring.append(bm.verts.new((cx + rx * math.copysign(abs(c) ** (2 / p), c),
                                      y, cz + rz * math.copysign(abs(s) ** (2 / p), s))))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return finish(mesh_object(name, bm), mat, bevel)


def smooth(pts, k=8):
    """The Catmull-Rom curve through `pts`, (y, z) points, as `k` straight pieces between each two."""
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for s in range(k):
            t = s / k
            out.append(tuple(0.5 * (2 * p1[d] + (p2[d] - p0[d]) * t + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t * t
                                    + (3 * p1[d] - p0[d] - 3 * p2[d] + p3[d]) * t ** 3) for d in range(2)))
    out.append(pts[-1])
    return out


def strip(name, mat, line, thick, width, x=0.0, bevel=0.0008):
    """A strip `thick` deep (in the side plane) and `width` across X, swept along the side curve through
    `line`, (y, z) points."""
    line = smooth(line)
    bm = bmesh.new()
    rings = []
    for i, (y, z) in enumerate(line):
        a = line[max(i - 1, 0)]
        b = line[min(i + 1, len(line) - 1)]
        ty, tz = b[0] - a[0], b[1] - a[1]
        l = math.hypot(ty, tz)
        ny, nz = -tz / l * thick / 2, ty / l * thick / 2
        rings.append([bm.verts.new((x + sx * width / 2, y + sn * ny, z + sn * nz)) for sx, sn in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for a, b in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return finish(mesh_object(name, bm), mat, bevel)


def along(table, y):
    """The value at `y` of the curve through `table`, (y, value) points in either order of y."""
    pts = sorted(smooth(sorted(table)), key=lambda p: p[0])
    if y <= pts[0][0]:
        return pts[0][1]
    for (y0, v0), (y1, v1) in zip(pts, pts[1:]):
        if y <= y1:
            return v0 + (v1 - v0) * (y - y0) / ((y1 - y0) or 1)
    return pts[-1][1]


def sweep(name, mat, axis, half, n=40, bevel=0.0, upright=False):
    """Cross sections along the side curve `axis`, (y, z) points: at each, a superellipse across X by
    `half(t)` → (rx, rn, p), rx its half-width across the gun, rn its half-depth in the side plane
    square to the curve (or, `upright`, straight up and down, the section standing square to the bore
    whichever way the curve runs), p its power, for t from 0 at the first point to 1 at the last;
    capped at both ends. A curve of few points is smoothed through them; an upright one is taken as
    given, its points already as close as its sections are meant to be."""
    if not upright:
        axis = smooth(axis, 6)
    bm = bmesh.new()
    rings = []
    m = len(axis)
    for i, (y, z) in enumerate(axis):
        a, b = axis[max(i - 1, 0)], axis[min(i + 1, m - 1)]
        ty, tz = b[0] - a[0], b[1] - a[1]
        l = math.hypot(ty, tz)
        ny, nz = (0.0, 1.0) if upright else (-tz / l, ty / l)
        rx, rn, p = half(i / (m - 1))
        ring = []
        for k in range(n):
            ang = 2 * math.pi * k / n
            c, s = math.cos(ang), math.sin(ang)
            ex = rx * math.copysign(abs(c) ** (2 / p), c)
            en = rn * math.copysign(abs(s) ** (2 / p), s)
            ring.append(bm.verts.new((ex, y + ny * en, z + nz * en)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return finish(mesh_object(name, bm), mat, bevel)


def box(name, mat, sx, sy, sz, x, y, z, bevel=0.001):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(sx, sy, sz))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x, y, z))
    return finish(mesh_object(name, bm), mat, bevel)


def ball(name, mat, r, at, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r)
    bmesh.ops.scale(bm, verts=bm.verts, vec=scale)
    bmesh.ops.translate(bm, verts=bm.verts, vec=at)
    return finish(mesh_object(name, bm), mat, 0)


def across(name, mat, r, x0, x1, y, z, sides=16, bevel=0.0004):
    """A cylinder across the gun, along X from x0 to x1, its axis at (y, z): a pin or a button."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r, radius2=r, depth=x1 - x0)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__('mathutils').Matrix.Rotation(math.pi / 2, 3, 'Y'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=((x0 + x1) / 2, y, z))
    return finish(mesh_object(name, bm), mat, bevel)


# The empties, made once the parts are joined, so a part of the same name (the grip, the stock) is
# gone by then and the empty takes its name.
empties = []


def empty(name, at, turn=(1, 0, 0, 0)):
    empties.append((name, at, turn))


def build(name, muzzle, length, tris, preview_middle=(0, 0.14, 0.02)):
    """Joins the parts as `name`, asserts it is no more than `tris` triangles, `length` (lo, hi) metres
    butt to muzzle, and ends at `muzzle`, writes the glb, and renders the previews."""
    bpy.ops.object.select_all(action='DESELECT')
    for ob in parts:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    gun = bpy.context.active_object
    gun.name = name
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    for e, at, turn in empties:
        bpy.ops.object.empty_add(location=at)
        ob = bpy.context.active_object
        ob.name = e
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = turn

    dg = bpy.context.evaluated_depsgraph_get()
    ev = gun.evaluated_get(dg).to_mesh()
    ev.calc_loop_triangles()
    count = len(ev.loop_triangles)
    ys = [v.co.y for v in ev.vertices]
    long = max(ys) - min(ys)
    tip = max(ys)
    gun.evaluated_get(dg).to_mesh_clear()
    print(f'TRIS {name}={count} max={tris} {"OK" if count <= tris else "FAIL"}')
    print(f'LENGTH butt={min(ys):.3f} muzzle={tip:.3f} length={long:.3f} {"OK" if length[0] <= long <= length[1] else "FAIL"}')
    print(f'MUZZLE empty={muzzle:.3f} mesh={tip:.3f} {"OK" if abs(tip - muzzle) < 0.002 else "FAIL"}')
    if count > tris or not (length[0] <= long <= length[1]) or abs(tip - muzzle) >= 0.002:
        raise SystemExit(f'{name}: an assert failed')

    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_yup=True, export_apply=True,
                              export_animations=False, export_image_format='JPEG')
    print(f'{name}: wrote {OUT}')

    if not PREVIEW:
        return
    os.makedirs(PREVIEW, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.view_settings.view_transform = 'Standard'
    sc.world = bpy.data.worlds.new('w')
    sc.world.use_nodes = True
    sc.world.node_tree.nodes['Background'].inputs[0].default_value = (0.42, 0.46, 0.52, 1)
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = 0.8
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam)
    sc.camera = cam

    def shot(shot_name, at, lens=50, mid=Vector(preview_middle)):
        cam.data.lens = lens
        cam.location = at
        cam.rotation_euler = (mid - Vector(at)).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREVIEW, shot_name + '.png')
        bpy.ops.render.render(write_still=True)

    mid = Vector(preview_middle)
    for a in (30, 120, 210, 300):
        t = math.radians(a)
        shot(f'turn-{a}', (mid.x + 1.6 * math.cos(t), mid.y + 1.6 * math.sin(t), mid.z + 0.5))
    shot('right', (1.4, mid.y, mid.z), 60)
    shot('left', (-1.4, mid.y, mid.z), 60)
    shot('receiver', (0.45, 0.02, 0.12), 60, Vector((0, 0.04, 0.04)))
    shot('first', (0.0, -0.45, 0.2), 35, Vector((0, 0.3, 0.08)))


# ---------- the gun ----------

# The receiver: flat-bottomed, its top rising from the rear in a curve and running flat to the face,
# its long edges rounded. The ejection port on its right, dark, with the bright bolt showing in it, and
# the loading port under it; the trigger plate's two pins through its sides.
R0, R1 = RECEIVER
profile('receiver', BLUED, [(R0, 0.03), (R1, 0.03), (R1, 0.105)] + smooth([(R1, 0.105), (R1 - 0.008, 0.1115),
                            (0.03, 0.1125), (R0 + 0.03, 0.109), (R0 + 0.008, 0.1), (R0, 0.09)], 4)[1:-1],
        0.036, bevel=0.007, segments=6)
box('port', DARK, 0.002, 0.07, 0.025, 0.0172, 0.083, 0.084, bevel=0.0006)
box('bolt', BRIGHT, 0.002, 0.046, 0.015, 0.0178, 0.074, 0.084, bevel=0.0008)
box('lug', BRIGHT, 0.0024, 0.008, 0.006, 0.0182, 0.06, 0.084, bevel=0.0006)
box('loading', DARK, 0.024, 0.09, 0.002, 0, 0.095, 0.0296, bevel=0.0005)
for y in (0.004, 0.118):
    across(f'pin{y}', BRIGHT, 0.0024, -0.0186, 0.0186, y, 0.042)

# The barrel: a shroud where it meets the receiver, then the tube, bored at the mouth.
tube('shroud', BLUED, 0.0165, R1 - 0.002, R1 + 0.034, BORE, sides=32, bevel=0.0012)
tube('barrel', BLUED, BARREL, R1 + 0.03, MUZZLE, BORE, sides=32, hollow=0.0028, depth=0.04)

# The vent rib along the top of the barrel on its posts, a brass bead at its front and a mid bead.
rib_top = SIGHT - 0.0035
box('rib', BLUED, 0.0075, MUZZLE - 0.012 - (R1 + 0.005), 0.0028, 0, (MUZZLE - 0.012 + R1 + 0.005) / 2, rib_top - 0.0014, bevel=0.0006)
post_y = R1 + 0.02
while post_y < MUZZLE - 0.01:
    box(f'post{post_y:.3f}', BLUED, 0.004, 0.006, rib_top - 0.0028 - (BORE + BARREL) + 0.002, 0, post_y, (rib_top - 0.0028 + BORE + BARREL - 0.002) / 2, bevel=0.0004)
    post_y += 0.03
ball('bead', BRASS, 0.0024, (0, MUZZLE - 0.016, SIGHT))
ball('midbead', BRIGHT, 0.0014, (0, 0.38, rib_top + 0.0008))

# The magazine tube under the barrel, the hanger that clamps it to the barrel, and its cap.
tube('tube', BLUED, 0.0112, R1, 0.556, TUBE, sides=24)
loft('hanger', BLUED, [(0.535, 0, (BORE + TUBE) / 2, 0.0145, (BORE - TUBE) / 2 + 0.0135, 3.2),
                       (0.552, 0, (BORE + TUBE) / 2, 0.0145, (BORE - TUBE) / 2 + 0.0135, 3.2)], bevel=0.0008)
tube('cap', BLUED, 0.0128, 0.556, 0.578, TUBE, sides=24, bevel=0.0015)
for i in range(18):
    a = 2 * math.pi * i / 18
    box(f'knurl{i}', BLUED, 0.0016, 0.016, 0.0016, math.cos(a) * 0.0128, 0.567, TUBE + math.sin(a) * 0.0128, bevel=0)
ball('capnose', BLUED, 0.0105, (0, 0.578, TUBE), scale=(1, 0.5, 1))

# The forend: walnut round the tube and up the barrel's sides, ribbed with a groove every `GROOVE`
# metres, rounded at both ends; a steel nut at its front, and the two action bars running back from
# it into the receiver.
GROOVE = 0.017
F0, F1 = FOREND
st = []
y = F0
while y <= F1 + 1e-6:
    t = (y - F0) / (F1 - F0)
    end = min(t, 1 - t)
    shrink = 0.86 + 0.14 * min(1.0, end / 0.06) ** 0.5
    groove = ((y - F0) % GROOVE) / GROOVE
    dip = 0.93 if 0.35 < groove < 0.65 and 0.08 < t < 0.92 else 1.0
    st.append((y, 0, PUMP_AT + 0.004, 0.0245 * shrink * dip, 0.026 * shrink * dip, 2.6))
    y += GROOVE / 6
loft('forend', WALNUT, st, n=40)
tube('nut', BLUED, 0.0122, F1 - 0.002, F1 + 0.008, TUBE, sides=24, bevel=0.001)
for side in (-1, 1):
    box(f'bar{side}', BRIGHT, 0.002, F0 - R1 + 0.01, 0.006, side * 0.0135, (F0 + R1) / 2, TUBE + 0.002, bevel=0.0005)

# The trigger plate under the receiver, the guard swept round the trigger, the trigger, and the safety
# through the guard's top.
box('plate', BLUED, 0.03, 0.075, 0.008, 0, TRIGGER + 0.002, 0.027, bevel=0.0015)
strip('guard', BLUED, [(TRIGGER + 0.034, 0.026), (TRIGGER + 0.034, 0.012), (TRIGGER + 0.026, 0.0),
                       (TRIGGER + 0.01, -0.008), (TRIGGER - 0.012, -0.008), (TRIGGER - 0.026, 0.0),
                       (TRIGGER - 0.032, 0.014), (TRIGGER - 0.034, 0.026)], 0.0045, 0.011, bevel=0.0012)
strip('trigger', BRIGHT, [(TRIGGER - 0.002, 0.026), (TRIGGER + 0.0, 0.014), (TRIGGER - 0.004, 0.004),
                          (TRIGGER - 0.011, -0.002)], 0.0042, 0.006, bevel=0.0008)
across('safety', BRIGHT, 0.0032, -0.016, 0.016, TRIGGER + 0.026, 0.031)


# The stock: walnut, from the receiver's rear back to the pad, a pistol grip whose middle is the hold,
# every long edge rounded and the whole narrower at the wrist than at the butt (`stock_width`).
# The butstock is lofted: at every `STATION` metres from under the receiver back to the spacer, an oval
# section from its belly (`BELLY`) up to its comb (`COMB`), `WIDTH` across, squarer (`POWER`) where it
# meets the receiver's flat sides and rounder down the wrist. Its belly rises behind the grip into the
# throat, runs along the wrist and falls to the toe. The pistol grip is a loft of its own down a raked
# axis (`GRIP_AXIS`) through the hold, swelling for the palm, its foot capped in steel; where it and the
# stock meet they run into each other under the receiver.
STOCK_END = BUTT + 0.016     # the stock's rear face, where the spacer starts
SPACER_END = BUTT + 0.013    # the spacer's rear face, where the pad starts
STOCK_FRONT = 0.008          # where the stock's loft starts, its face hidden in the grip and the receiver
COMB = [(STOCK_FRONT, 0.07), (R0, 0.098), (-0.09, 0.095), (-0.15, 0.092), (-0.22, 0.089), (STOCK_END, 0.086)]
BELLY = [(STOCK_FRONT, 0.012), (-0.01, 0.004), (-0.026, -0.008), (-0.04, -0.03), (-0.05, -0.044), (-0.06, -0.04),
         (-0.072, -0.02), (-0.088, 0.004), (-0.11, 0.014), (-0.14, 0.006), (-0.2, -0.028),
         (-0.25, -0.056), (STOCK_END, -0.072)]
WIDTH = [(STOCK_FRONT, 0.026), (-0.01, 0.029), (-0.03, 0.029), (R0, 0.031), (-0.07, 0.033), (-0.09, 0.034), (-0.16, 0.038), (STOCK_END, 0.044)]
POWER = [(STOCK_FRONT, 3.0), (R0, 3.2), (-0.085, 2.4), (-0.2, 2.5), (STOCK_END, 2.7)]
STATION = 0.005
GRIP_AXIS = [(0.006, 0.032), (-0.002, 0.0), (-0.017, -0.034), (-0.03, -0.056)]


def stock_section(y):
    top, bot = along(COMB, y), along(BELLY, y)
    return (y, (top + bot) / 2, along(WIDTH, y) / 2, (top - bot) / 2, along(POWER, y))


def stock_loft(name, mat, y0, y1, shrink=lambda t: 1.0):
    """The stock's sections from y0 back to y1, each scaled by `shrink(t)`, t 0 at y0 and 1 at y1."""
    count = max(2, int(round(abs(y1 - y0) / STATION)) + 1)
    secs = [stock_section(y0 + (y1 - y0) * i / (count - 1)) for i in range(count)]
    axis = [(y, z) for y, z, _, _, _ in secs]

    def half(t):
        i = min(count - 1, int(round(t * (count - 1))))
        _, _, rx, rn, p = secs[i]
        k = shrink(t)
        return rx * k, rn * k, p
    return sweep(name, mat, axis, half, n=48, upright=True)


stock_loft('stock', WALNUT, STOCK_FRONT, STOCK_END)
sweep('grip', WALNUT, GRIP_AXIS, lambda t: (0.0148 + 0.0016 * math.sin(math.pi * t), 0.0205 + 0.0025 * math.sin(math.pi * t), 2.3), n=40)
gy, gz = GRIP_AXIS[-1]
dy, dz = gy - GRIP_AXIS[-2][0], gz - GRIP_AXIS[-2][1]
dl = math.hypot(dy, dz)
sweep('gripcap', BLUED, [(gy - dy / dl * 0.001, gz - dz / dl * 0.001), (gy + dy / dl * 0.003, gz + dz / dl * 0.003)],
      lambda t: (0.0149 - 0.001 * t, 0.0206 - 0.001 * t, 2.3), n=40)

# The white spacer and the rubber pad, each the stock's own last section carried on; the pad's rear edge
# rounded in, and ribbed across its face.
stock_loft('spacer', SPACER, STOCK_END + 0.0002, SPACER_END)
stock_loft('pad', RUBBER, SPACER_END + 0.0002, BUTT, shrink=lambda t: 1.0 - 0.06 * max(0.0, (t - 0.6) / 0.4) ** 2)
_, pad_z, pad_rx, pad_rz, _ = stock_section(STOCK_END)
for i in range(9):
    z = pad_z - pad_rz * 0.8 + i * pad_rz * 1.6 / 8
    box(f'padrib{i}', RUBBER, pad_rx * 1.4, 0.002, 0.0035, 0, BUTT - 0.0004, z, bevel=0.0007)

empty('muzzle', (0, MUZZLE, BORE))
empty('stock', STOCK)
empty('grip', GRIP, GRIP_TURN)
empty('support', (-0.0418, SUPPORT, PUMP_AT - (UNDER - (0.026 - PUMP))), SUPPORT_TURN)
empty('eye', (0, EYE, SIGHT))

build('shotgun', MUZZLE, (0.89, 0.94), 40000)
