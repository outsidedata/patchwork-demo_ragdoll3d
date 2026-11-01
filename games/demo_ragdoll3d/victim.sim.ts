// A body standing still in its idle, animated by anim, which draws it, until something kills it: then
// it lies limp as a box3d ragdoll (ragdoll3d's physics mode), and anim neither draws nor moves it.
//
// The row: `pos`, `yaw`, `vel`, `grounded`, `limp`, which anim reads; `rig`; anim's own fields;
// ragdoll3d's `limpFor`, `blow`, `pose` and `ragdoll` while it lies.
//
// `hit(struck)`, a rule's (seat −1), hitscan3d's `Struck` with the weapon's `impulse`: it dies
// (ragdoll3d's `die`), a push of `impulse` N·s along the shot put on the bone it struck at the point it
// struck, and no blow of its own.
// `die()`, a rule's: it dies with no push, as the TNT kills it (`tnt.sim.ts`), whose blast throws it.
// `stand()`: it rises (ragdoll3d's `rise`) and stands again in its idle where it stood. It stands again
// by itself once it has lain its definition's `again` seconds.
import type { Kind } from '#engine/engine.ts'
import { animate, rest } from '#plugins/anim/anim.sim.ts'
import { def } from '#plugins/loader/loader.sim.ts'
import { die, lie, rise } from '#plugins/ragdoll3d/ragdoll3d.sim.ts'
import type { Struck } from '#plugins/hitscan3d/hitscan3d.sim.ts'

export const victim: Kind = {
  tick(me, dt, w) {
    if (me.data.limp) {
      lie(me)
      if (me.data.limpFor * dt >= def(w, me.kind).again) w.call(me, 'stand', -1)
      return
    }
    animate(me, w, dt)
  },
  acts: {
    hit(me, w, seat, h: Struck & { impulse: number }) {
      if (seat !== -1 || me.data.limp || h.part === null) return
      die(w, me, { dir: [0, 0], speed: 0, height: 0 }, [{ bone: h.part, point: h.point, impulse: h.dir.map(v => v * h.impulse) }])
    },
    die(me, w) {
      die(w, me, { dir: [0, 0], speed: 0, height: 0 }, [])
    },
    stand(me, w) {
      if (!me.data.limp) return
      rise(w, me)
      rest(me)
    },
  },
}
