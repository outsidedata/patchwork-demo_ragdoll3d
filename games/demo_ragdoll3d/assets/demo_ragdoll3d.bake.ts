// demo_ragdoll3d's bake, `yarn bake demo_ragdoll3d` (core's `scripts/bake.ts`): every clip of
// `farmer.rig.json` baked onto the body its `bodies` names (characters/xbot) by anim's export
// (`plugins/anim/anim.export.py`), which packs it with gltfpack into `farmer.glb` beside the rig, and
// the rig's `table` measured on it and written back into the rig in its own layout
// (`.claude/skills/using-mixamo-assets/scripts/merge-table.mjs`); and `shotgun.glb`, the shotgun built
// by its script (`shotgun.py`) in Blender from the maps of two cc0-textures sets (`GUN_SETS`, the
// library's, fetched by `texture` and cut to `GUN_MAPS` pixels) and packed by gltfpack, its empties kept
// by name; `tnt.glb` and `dynamite.glb`, the block of TNT and the stick of dynamite, each built by its
// script (`tnt.py`, `dynamite.py`) to the numbers the game draws and moves it by and packed by gltfpack;
// and
// `checker-1024.webp`, the floor's checkerboard, drawn here from nothing: `squares` squares a side in two
// greys, `light` and `dark`, each with a `line` pixel rim of `rim` grey, so a repeat of the map is
// `squares` squares across.
import { execFileSync } from 'node:child_process'
import fs, { readFileSync } from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'
import type { Tools } from '#scripts/bake.ts'

const here = import.meta.dirname
const repo = path.join(here, '..', '..', '..')

const SIZE = 1024
const CHECKER = { squares: 2, light: 0xd4, dark: 0xa8, rim: 0x86, line: 3 }

// A PNG of grey pixels, `size` a side: its signature, IHDR, one IDAT of the filtered rows, IEND.
function png(size: number, grey: (x: number, y: number) => number): Buffer {
  const table = new Uint32Array(256).map((_, n) => {
    let c = n
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    return c >>> 0
  })
  const crc = (b: Buffer) => {
    let c = 0xffffffff
    for (const v of b) c = table[(c ^ v) & 0xff] ^ (c >>> 8)
    return (c ^ 0xffffffff) >>> 0
  }
  const chunk = (type: string, data: Buffer) => {
    const head = Buffer.alloc(4)
    head.writeUInt32BE(data.length)
    const body = Buffer.concat([Buffer.from(type, 'ascii'), data])
    const tail = Buffer.alloc(4)
    tail.writeUInt32BE(crc(body))
    return Buffer.concat([head, body, tail])
  }
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0)
  ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8 // bits a sample
  ihdr[9] = 0 // greyscale
  const rows = Buffer.alloc(size * (size + 1))
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) rows[y * (size + 1) + 1 + x] = grey(x, y)
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(rows)),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

// The shotgun's two cc0-textures sets, its wood and its steel, in the order `shotgun.py` takes their
// maps, and the pixels a side each map is cut to.
const GUN_SETS = [['Wood066_4K-JPG', 'wood'], ['Metal010_4K-JPG', 'steel']] as const
const GUN_MAPS = 1024

export default async ({ blender, pack, webp, scratch, texture }: Tools) => {
  // the checkerboard
  const cell = SIZE / CHECKER.squares
  const raw = scratch('checker.png')
  fs.writeFileSync(raw, png(SIZE, (x, y) => {
    const i = Math.floor(x / cell), j = Math.floor(y / cell)
    const u = x - i * cell, v = y - j * cell
    const edge = Math.min(u, v, cell - 1 - u, cell - 1 - v) < CHECKER.line
    return edge ? CHECKER.rim : (i + j) % 2 ? CHECKER.dark : CHECKER.light
  }))
  const checker = path.join(here, `checker-${SIZE}.webp`)
  await webp(raw, checker, SIZE)
  console.log('wrote', path.relative(repo, checker))

  // the shotgun, its walnut and its blued steel each a cc0-textures set's maps cut to `GUN_MAPS` pixels
  const maps: string[] = []
  for (const [set, name] of GUN_SETS) {
    const got = await texture(set)
    for (const map of ['color', 'roughness', 'normal'] as const) {
      const from = got[map]
      if (!from) throw new Error(`${set} has no ${map} map`)
      const cut = scratch(`${name}-${map}.webp`)
      await webp(from, cut, GUN_MAPS)
      maps.push(cut)
    }
  }
  const built = scratch('shotgun.glb')
  console.log(await blender(['--factory-startup', '--python-exit-code', '1', '--python', path.join(here, 'shotgun.py'), '--', built, ...maps]))
  const gun = path.join(here, 'shotgun.glb')
  await pack(built, gun)
  console.log('wrote', path.relative(repo, gun))

  // the block of TNT, built to its definition's `size`, and the stick of dynamite, to its box3d body's
  // cylinder and its definition's `fuse.root`
  const defs = JSON.parse(readFileSync(path.join(here, 'demo_ragdoll3d.json'), 'utf8'))
  const blast = JSON.parse(readFileSync(path.join(here, '..', 'blast.scene.json'), 'utf8'))
  const stick = blast.world.box3d.kinds.dynamite.shapes[0].cylinder
  for (const [name, args] of [
    ['tnt', [String(defs.tnt.size)]],
    ['dynamite', [String(stick.radius), String(stick.height), String(defs.dynamite.fuse.root)]],
  ] as const) {
    const raw = scratch(`${name}.glb`)
    console.log(await blender(['--factory-startup', '--python-exit-code', '1', '--python', path.join(here, `${name}.py`), '--', raw, ...args]))
    const out = path.join(here, `${name}.glb`)
    await pack(raw, out)
    console.log('wrote', path.relative(repo, out))
  }

  const rig = path.join(here, 'farmer.rig.json'), table = scratch('farmer.table.json')
  const bodies = Object.keys(JSON.parse(readFileSync(rig, 'utf8')).bodies)
  await blender(['--factory-startup', '--python-exit-code', '1', '--python', path.join(repo, 'plugins', 'anim', 'anim.export.py'), '--',
    rig, table, ...bodies.map(b => `${b}=${path.join(here, `${b}.glb`)}`)])
  execFileSync(process.execPath, [path.join(repo, '.claude', 'skills', 'using-mixamo-assets', 'scripts', 'merge-table.mjs'), rig, table, rig], { stdio: 'inherit' })
}
