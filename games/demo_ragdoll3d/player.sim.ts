// The row one seat possesses: the seat's eye and the shotgun it carries. `addons/player` spawns it when
// a connection takes a slot and writes that slot into `seat`.
//
// The row: `pos` (x, y, z metres), the pivot; `yaw` (radians, yaw θ faces (sin θ, cos θ)) and `pitch`
// (radians, positive up), where it points; `aim`, [yaw, pitch], where it is wanted to point, which the
// seat's look moves, and which it turns toward each step by its definition's `turn`: `lerp` × the step's
// seconds of the way left, no faster than `slew` radians a second about each axis (null until its first
// step, when it takes where it points); `walk`, [ahead, aside] as the seat holds them, each step moving
// it its definition's `walk` m/s, ahead along its `yaw` and to its left; `firing`, the trigger held;
// `cool`, the seconds before the shotgun may fire again.
//
// The view: the eye is the definition's `eye` (metres in the row's frame, turned by its `yaw` and
// `pitch`: x left, y up, z ahead) and looks along the aim, as the seat's look puts render3d's camera
// (`player.client.ts`). A pull while `firing` and cool fires the definition's `shotgun`: one hitscan3d
// shot from the eye along the aim within `range` metres, its hurt `{ damage, by: the row, impulse }`,
// so a standing victim's bone it meets is hit (the victim's `hit`); a standing block of TNT nearer
// than anything else the shot meets stops it and is set off (the block's `hit`); and the gun is ready again after
// `cooldown` seconds. Each pull throws three of particle3d's effects: `flash` at the muzzle along the
// aim, `tracer` from the muzzle to where the shot ended, and `dirt` where it met the ground or a solid,
// along that surface's normal. The muzzle is the shotgun's `muzzle`, metres right, up and back of the
// eye as the view faces, where the look's model holds its `muzzle` empty.
//
// The acts are the seat's mouse and keys: `ahead(v)` and `aside(v)` (−1 to 1) walk it; `look(dyaw,
// dpitch)` turns the row's `aim` by that much (radians), its pitch kept within its definition's `pitch`
// [least, most]; `fire(v)` (1 held, 0 let go); `drop()`, a lit stick of dynamite let go of before its
// feet (`drop`, below), and `throw()`, one thrown along the aim (`hurl`), each no sooner than its
// definition's `drop.every` seconds after the last stick, which `dropCool` counts down. `blast(x, y, z,
// radius, falloff, speed)` is a rule's (a block of TNT's or a stick's going off) and throws the row
// through the air: `vel`, falling by `launch.gravity` down to `launch.stand`, the pivot's height when
// standing, where it lands and stops. A seat's message comes from outside the program, so each refuses what is not a
// number in its range.
import type { Kind, Row, W } from '#engine/engine.ts'
import { def } from '#plugins/loader/loader.sim.ts'
import { shoot } from '#plugins/hitscan3d/hitscan3d.sim.ts'
import { lineBox } from '#plugins/shapes3d/shapes3d.sim.ts'
import { emit } from '#plugins/particle3d/particle3d.sim.ts'
import * as math from '#plugins/math/math.sim.ts'

const turned = (v: unknown) => typeof v === 'number' && Number.isFinite(v) && Math.abs(v) <= Math.PI
const held = (v: unknown) => typeof v === 'number' && Number.isFinite(v) && Math.abs(v) <= 1

// The eye in the world: the definition's `eye` in the row's frame, turned by its pitch, then its yaw.
function eyeOf(d: Record<string, any>, eye: number[]): number[] {
  const cp = math.cos(-d.pitch), sp = math.sin(-d.pitch)
  const x = eye[0], y = eye[1] * cp - eye[2] * sp, z = eye[1] * sp + eye[2] * cp
  const cy = math.cos(d.yaw), sy = math.sin(d.yaw)
  return [d.pos[0] + x * cy + z * sy, d.pos[1] + y, d.pos[2] - x * sy + z * cy]
}

// One pull of the shotgun.
function pull(me: Row, w: W, k: Record<string, any>) {
  const d = me.data
  const g = k.shotgun
  d.cool = g.cooldown
  const [yaw, pitch] = d.aim ?? [d.yaw, d.pitch]
  const cp = math.cos(pitch)
  const f = [math.sin(yaw) * cp, math.sin(pitch), math.cos(yaw) * cp]
  const from = eyeOf(d, k.eye)
  // The view's frame: right, up, and back (the way the view faces is its −back).
  const right = [-f[2] / cp, 0, f[0] / cp]
  const back = [-f[0], -f[1], -f[2]]
  const up = [back[1] * right[2] - back[2] * right[1], back[2] * right[0] - back[0] * right[2], back[0] * right[1] - back[1] * right[0]]
  const m = g.muzzle
  const muzzle = [0, 1, 2].map(i => from[i] + right[i] * m[0] + up[i] * m[1] + back[i] * m[2])
  // The nearest standing block of TNT on the line, which stops the shot and is set off.
  let block: { row: Row; t: number } | undefined
  for (const t of w.all('tnt')) {
    if (t.data.out > 0) continue
    const s = def(w, t.kind).size
    const at = lineBox({ pos: t.data.pos, size: [s, s, s], yaw: t.data.yaw }, from, f, block?.t ?? g.range, 0)
    if (at) block = { row: t, t: at.t }
  }
  const met = shoot(w, from, f, block?.t ?? g.range, { hurt: { damage: g.damage, by: me.id, impulse: g.impulse } })
  if (block && !met) w.call(block.row, 'hit', -1)
  const end = met ? met.point : from.map((v, i) => v + f[i] * (block?.t ?? g.range))
  emit(w, 'flash', muzzle, { dir: f })
  emit(w, 'tracer', muzzle, { to: end })
  if (met && met.what !== 'body') emit(w, 'dirt', met.point, { dir: met.normal })
}

export const player: Kind = {
  tick(me, dt, w) {
    const d = me.data
    const k = def(w, me.kind)
    // Turned toward the aim by its own `turn`.
    if (!d.aim) d.aim = [d.yaw, d.pitch]
    else {
      const most = k.turn.slew * dt, share = Math.min(1, k.turn.lerp * dt)
      const dyaw = math.atan2(math.sin(d.aim[0] - d.yaw), math.cos(d.aim[0] - d.yaw))
      const yaw = d.yaw + Math.max(-most, Math.min(most, dyaw * share))
      const pitch = d.pitch + Math.max(-most, Math.min(most, (d.aim[1] - d.pitch) * share))
      if (yaw !== d.yaw) d.yaw = yaw
      if (pitch !== d.pitch) d.pitch = pitch
    }
    // Walked: ahead (sin, cos) of the yaw, left (cos, −sin).
    const [ahead, left] = d.walk
    const s = math.sin(d.yaw), c = math.cos(d.yaw), step = k.walk * dt
    d.pos = [d.pos[0] + (s * ahead + c * left) * step, d.pos[1], d.pos[2] + (c * ahead - s * left) * step]
    // Thrown: carried by `vel`, falling by `launch.gravity`, until it is back down at its standing
    // height, where it stops dead.
    const L = k.launch
    const [vx, vy, vz] = d.vel
    if (vx || vy || vz) {
      const fall = vy - L.gravity * dt
      const y = d.pos[1] + fall * dt
      const down = y <= L.stand
      d.pos = [d.pos[0] + vx * dt, down ? L.stand : y, d.pos[2] + vz * dt]
      d.vel = down ? [0, 0, 0] : [vx, fall, vz]
    }
    d.cool = Math.max(0, d.cool - dt)
    d.dropCool = Math.max(0, d.dropCool - dt)
    if (d.firing && d.cool === 0) pull(me, w, k)
  },
  acts: {
    ahead(me, _w, _seat, v: unknown) {
      if (held(v)) me.data.walk = [v, me.data.walk[1]]
    },
    aside(me, _w, _seat, v: unknown) {
      if (held(v)) me.data.walk = [me.data.walk[0], v]
    },
    look(me, w, _seat, dyaw: unknown, dpitch: unknown) {
      if (!turned(dyaw) || !turned(dpitch)) return
      const d = me.data
      const range = def(w, me.kind).pitch
      const [yaw, pitch] = d.aim ?? [d.yaw, d.pitch]
      d.aim = [yaw + (dyaw as number), Math.min(range[1], Math.max(range[0], pitch + (dpitch as number)))]
    },
    fire(me, _w, _seat, v: unknown) {
      if (v !== 0 && v !== 1) return
      me.data.firing = v === 1
    },
    drop(me, w) {
      if (me.data.dropCool > 0) return
      const k = def(w, me.kind).drop
      me.data.dropCool = k.every
      drop(me, w, k)
    },
    // A blast at (x, y, z), a rule's alone (seat −1): the row thrown away from it and up, `speed` m/s
    // within `radius` metres, less by how far past it out to `radius + falloff`, nothing beyond; the
    // definition's `launch.up` of it straight up and the rest out along the ground.
    blast(me, w, seat, x: number, y: number, z: number, radius: number, falloff: number, speed: number) {
      if (seat >= 0) return
      const d = me.data
      const L = def(w, me.kind).launch
      const dx = d.pos[0] - x, dz = d.pos[2] - z
      const far = math.hypot(dx, d.pos[1] - L.stand - y, dz)
      const share = far <= radius ? 1 : falloff > 0 ? Math.max(0, 1 - (far - radius) / falloff) : 0
      if (share === 0) return
      const flat = math.hypot(dx, dz)
      const out = speed * share * (1 - L.up), lift = speed * share * L.up
      const [ox, oz] = flat > 0 ? [dx / flat * out, dz / flat * out] : [0, 0]
      d.vel = [d.vel[0] + ox, Math.max(0, d.vel[1]) + lift, d.vel[2] + oz]
    },
    throw(me, w) {
      if (me.data.dropCool > 0) return
      const k = def(w, me.kind)
      me.data.dropCool = k.drop.every
      hurl(me, w, k)
    },
  },
}

// A stick pointing the way `yaw` faces: its long axis (its body's +Y) turned onto (s, 0, c), fuse
// first, by a quarter turn about (c, 0, −s), the axis across that way.
const along = (s: number, c: number) => [c * Math.SQRT1_2, 0, -s * Math.SQRT1_2, Math.SQRT1_2]

// A lit stick of dynamite let go of from the hand: a `dynamite` row spawned the definition's `drop.ahead`
// metres before the row's feet along its yaw, `drop.height` over the floor, pointing the way the row
// faces, and tossed on at `drop.toss` [ahead, up] m/s tumbling end over end, `drop.roll` radians a second
// about the axis across that way, (c, 0, −s); box3d takes it from there (`dynamite.sim.ts`).
function drop(me: Row, w: W, k: { ahead: number; height: number; toss: number[]; roll: number }) {
  const d = me.data
  const s = math.sin(d.yaw), c = math.cos(d.yaw)
  w.spawn('dynamite', {
    pos: [d.pos[0] + s * k.ahead, k.height, d.pos[2] + c * k.ahead],
    rot: along(s, c),
    vel: [s * k.toss[0], k.toss[1], c * k.toss[0]],
    spin: [c * k.roll, 0, -s * k.roll],
  })
}

// A lit stick thrown along the aim: spawned the definition's `throw.ahead` metres out from the eye along
// it, pointing along it, at `throw.speed` m/s along the aim plus `throw.lift` m/s up, tumbling end over
// end forward at `throw.roll` radians a second about the axis across it, (c, 0, −s).
function hurl(me: Row, w: W, k: Record<string, any>) {
  const d = me.data
  const t = k.throw
  const [yaw, pitch] = d.aim ?? [d.yaw, d.pitch]
  const cp = math.cos(pitch)
  const s = math.sin(yaw), c = math.cos(yaw)
  const f = [s * cp, math.sin(pitch), c * cp]
  const from = eyeOf(d, k.eye)
  w.spawn('dynamite', {
    pos: from.map((v, i) => v + f[i] * t.ahead),
    rot: along(s, c),
    vel: [f[0] * t.speed, f[1] * t.speed + t.lift, f[2] * t.speed],
    spin: [c * t.roll, 0, -s * t.roll],
  })
}
