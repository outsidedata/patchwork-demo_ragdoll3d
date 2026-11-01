// A block of TNT standing on the ground, its definition's `size` metres on a side, that goes off the
// step a shot meets it (its `hit`, which the shooter's rule calls) or its fuse runs out: every standing
// victim within its definition's `reach` metres dies (each one's own `die`, which leaves a box3d ragdoll
// where it stood), box3d's own explosion (its row's `explode`) goes off at the block's middle, throwing
// every body near it by how near it is: `blast.radius`, `blast.falloff` (metres), `blast.impulse` (per
// area), on every shape; every seat's `player` row is thrown by it (its `blast`, at the definition's
// `launch` m/s over the same radius and falloff); and particle3d's `boom` is thrown there and its `smoulder` left on the ground
// where it stood. The block is gone for its definition's `again` seconds, as long as the smoulder
// lasts, then stands again where it stood, as a victim stands again after lying `again` seconds.
//
// The row: `pos` (x, y, z metres), the middle of its bottom face; `yaw` (radians); `fuse`, the seconds
// left, or `WAIT` and more while it waits (the testbed's button sets it to 0); `out`, the seconds left
// before it stands again, 0 while it stands; `boom`, how many times it has gone off.
//
// `hit()`, a rule's (seat −1): it goes off now, unless it is gone.
import type { Kind, Row, W } from '#engine/engine.ts'
import { def } from '#plugins/loader/loader.sim.ts'
import { emit } from '#plugins/particle3d/particle3d.sim.ts'
import * as math from '#plugins/math/math.sim.ts'

// A fuse this long is never reached: the block waits.
const WAIT = 1e9

function blow(me: Row, w: W) {
  const d = me.data
  const k = def(w, me.kind)
  const middle = [d.pos[0], d.pos[1] + k.size / 2, d.pos[2]]
  for (const v of w.all('victim')) {
    if (v.data.limp) continue
    if (math.hypot(v.data.pos[0] - d.pos[0], v.data.pos[2] - d.pos[2]) > k.reach) continue
    w.call(v, 'die', -1)
  }
  w.call(w.find('box3d'), 'explode', -1, middle[0], middle[1], middle[2], k.blast.radius, k.blast.falloff, k.blast.impulse)
  for (const seat of w.all('player')) w.call(seat, 'blast', -1, middle[0], middle[1], middle[2], k.blast.radius, k.blast.falloff, k.launch)
  emit(w, 'boom', middle, { dir: [0, 1, 0], floor: d.pos[1] })
  emit(w, 'smoulder', d.pos, { dir: [0, 1, 0], floor: d.pos[1], life: k.again })
  d.boom += 1
  d.fuse = WAIT
  d.out = k.again
}

export const tnt: Kind = {
  tick(me, dt, w) {
    const d = me.data
    if (d.out > 0) {
      d.out = Math.max(0, d.out - dt)
      return
    }
    d.fuse -= dt
    if (d.fuse <= 0) blow(me, w)
  },
  acts: {
    hit(me, w, seat) {
      if (seat !== -1 || me.data.out > 0) return
      blow(me, w)
    },
  },
}
