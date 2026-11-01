// A stick of dynamite, lit: a box3d body (`world.box3d.kinds.dynamite`, a cylinder along its +Y), thrown
// down by a seat (`player.sim.ts`'s `drop`), that falls, bounces, rolls and is thrown about as every other
// body in box3d's world is. A stiff fuse stands straight out of its +Y end, its definition's `fuse.length`
// metres from `fuse.root` metres past the end (the brass ferrule it goes into), and burns down it in
// `fuse.burn` seconds: on the step the stick is spawned its rule throws particle3d's `fuse` from the
// fuse's tip, flying to its root in exactly `fuse.burn` seconds, and on the step `left` reaches 0 the
// spark is at the root and the stick goes off. Every step until then the rule puts the spark's line on
// the fuse where the stick now lies, so the spark rides the stick as it tumbles.
//
// When it goes off every standing victim within its definition's `reach` metres dies (each one's own
// `die`), box3d's own explosion goes off at the stick (`blast.radius`, `blast.falloff`, `blast.impulse`),
// every seat's `player` row is thrown by it (its `blast`, at the definition's `launch` m/s over the same
// radius and falloff), the particle3d effect its definition's `pop` names is thrown there, and the stick's row ends, which takes its
// body out of box3d's world. A block of TNT is not set off by it: only a shot or its own fuse does that
// (`tnt.sim.ts`).
//
// The row: box3d's `pos`, `rot`, `vel`, `spin` and `awake`; `left`, the seconds of fuse left; `spark`, the
// id of its `fuse` entry on particle3d's ledger, −1 before it is thrown.
import type { Kind, Row, W } from '#engine/engine.ts'
import { def } from '#plugins/loader/loader.sim.ts'
import { emit, entry } from '#plugins/particle3d/particle3d.sim.ts'
import * as math from '#plugins/math/math.sim.ts'

// Its cylinder as box3d holds it: `height` along its +Y, `radius`.
export const body = (w: W, kind: string): { height: number; radius: number } =>
  w.world.box3d.kinds[kind].shapes[0].cylinder

// `v` turned by the quaternion `q` [x, y, z, w].
function turn(q: number[], v: number[]): number[] {
  const [x, y, z, s] = q
  const tx = 2 * (y * v[2] - z * v[1]), ty = 2 * (z * v[0] - x * v[2]), tz = 2 * (x * v[1] - y * v[0])
  return [v[0] + s * tx + (y * tz - z * ty), v[1] + s * ty + (z * tx - x * tz), v[2] + s * tz + (x * ty - y * tx)]
}

// The fuse's root and tip in the world, where the stick now lies.
function fuse(me: Row, w: W): { root: number[]; tip: number[] } {
  const k = def(w, me.kind)
  const { height } = body(w, me.kind)
  const up = turn(me.data.rot, [0, 1, 0])
  const at = (m: number) => me.data.pos.map((p: number, i: number) => p + up[i] * m)
  return { root: at(height / 2 + k.fuse.root), tip: at(height / 2 + k.fuse.root + k.fuse.length) }
}

function blow(me: Row, w: W) {
  const k = def(w, me.kind)
  const p = me.data.pos
  for (const v of w.all('victim')) {
    if (v.data.limp) continue
    if (math.hypot(v.data.pos[0] - p[0], v.data.pos[2] - p[2]) > k.reach) continue
    w.call(v, 'die', -1)
  }
  w.call(w.find('box3d'), 'explode', -1, p[0], p[1], p[2], k.blast.radius, k.blast.falloff, k.blast.impulse)
  for (const seat of w.all('player')) w.call(seat, 'blast', -1, p[0], p[1], p[2], k.blast.radius, k.blast.falloff, k.launch)
  emit(w, k.pop, p, { dir: [0, 1, 0], floor: 0 })
  w.end(me)
}

export const dynamite: Kind = {
  tick(me, dt, w) {
    const d = me.data
    const k = def(w, me.kind)
    const { root, tip } = fuse(me, w)
    if (d.spark < 0) {
      d.left = k.fuse.burn
      d.spark = emit(w, 'fuse', tip, { to: root, fly: k.fuse.length / k.fuse.burn }).id
    } else {
      const e = entry(w, d.spark)
      if (e) {
        e.at = tip
        e.to = root
      }
    }
    d.left = Math.max(0, d.left - dt)
    if (d.left === 0) blow(me, w)
  },
}
