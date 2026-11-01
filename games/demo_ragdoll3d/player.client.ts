// The seat's eye, the `player` row, and the shotgun it carries. It draws nothing for another seat's row.
//
// For the row that is `mine` alone, the view, the gun and the controls. While nobody has claimed
// render3d's camera, it sits at the row's eye, the definition's `eye` (metres in the row's frame, turned
// by its `yaw` and `pitch`: x left, y up, z ahead), and looks along its aim; a ring of the definition's
// `reticle` (its sizes a share of the view's height at one metre) stays in the middle of the view. The
// shotgun, the loader's model the definition's `shotgun.model` names, is held in render3d's overlay,
// drawn over the world so it meets nothing of it: its grip at `shotgun.view.at` metres right, up and
// back of the camera as the camera faces, turned by `view.turn` degrees, the overlay's camera given
// `view.near` and `view.far`, and the overlay lit by the world's sun and sky. The flash, the tracer and
// the dirt of each pull are particle3d's, thrown by the rule (`player.sim.ts`).
//
// The keys are bound to the scene's actions (`world.player.actions` in `demo_ragdoll3d.scene.json`).
// W, A, S, D (or the arrows, or the left stick) walk it, sent as `ahead` and `aside`. A click on the
// page takes the pointer lock; under it the mouse sends `look`, its pixels times `sens` (right turns
// right, down tips down). The right stick aims too, read analog and kept on this page: for each step
// taken while it is pushed the page sends `look` turned by the push times the definition's `pad.look`
// [yaw, pitch] radians a second (`aiming`). The left button or the right bumper held fires. G, or the
// pad's X, drops a lit stick of dynamite (`drop`); the right button, or the pad's Y, throws one along
// the aim (`throw`).
import type { Row } from '#engine/engine.ts'
import type { Plugins } from '#engine/browser.ts'
import type { Controls } from '#plugins/player/player.plugin.ts'
import { def } from '#plugins/loader/loader.sim.ts'

const DEG = Math.PI / 180

let ours = false
let reticle: any
let gun: any
let asked = false
let lights: { sun: any; sky: any } | undefined
// The right stick as last read, x right and y down, each −1 to 1, and the step the aim was last sent
// on (`aiming`); undefined before the first.
let aim = [0, 0]
let aimed: number | undefined

export function setup(row: Row, plugins: Plugins) {
  const T = plugins.render3d.THREE
  const k = def(plugins.wire, row.kind)
  ours = row.data.mine === true
  gun = undefined
  asked = false
  lights = undefined
  if (!ours) return
  const r = k.reticle
  reticle = new T.Mesh(new T.RingGeometry(r.inner, r.outer, 32), new T.MeshBasicMaterial({ color: r.colour, depthTest: false, depthWrite: false }))
  reticle.renderOrder = 999
  reticle.frustumCulled = false
  plugins.render3d.scene.add(reticle)
  aim = [0, 0]
  aimed = undefined
  plugins.player.control({
    pointer: (dx, dy) => ['look', -dx * k.sens, -dy * k.sens],
    axis: { ahead: v => ['ahead', v], aside: v => ['aside', v] },
    stick: { look: (x, y) => { aim = [x, y]; return undefined } },
    hold: { fire: v => ['fire', v] },
    press: { drop: ['drop'], throw: ['throw'] },
    analog: ['ahead', 'aside', 'look'],
  } satisfies Controls)
}

// The right stick's aim, sent once for each step the page has taken since it last sent: `look` turned
// by the stick's push times the definition's `pad.look` [yaw, pitch] radians a second at the rim, for
// that many steps' seconds, no more than `pad.most` seconds (a tab hidden a while), so the view turns
// at the same rate however the frames fall. Right turns right and down tips down, as the mouse does.
// Steps gone back (the page's copy run again) send nothing and count from there.
function aiming(plugins: Plugins, k: any) {
  const n: number = plugins.wire.n
  const was = aimed
  aimed = n
  if (was === undefined || n <= was || (aim[0] === 0 && aim[1] === 0)) return
  const seconds = Math.min(k.pad.most, (n - was) * plugins.wire.scene.prefabs.engine.dt)
  plugins.player.look(-aim[0] * k.pad.look[0] * seconds, -aim[1] * k.pad.look[1] * seconds)
}

// The shotgun's model in the overlay, once the loader has it.
function held(plugins: Plugins, name: string) {
  if (gun) return gun
  const loader = plugins.loader
  if (!loader.ready(name)) {
    if (!asked) {
      asked = true
      loader.load(name).catch(() => {})
    }
    return undefined
  }
  gun = loader.model(name).scene
  gun.traverse((o: any) => {
    if (!o.isMesh) return
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) plugins.render3d.dress(m)
  })
  plugins.render3d.overlay.scene.add(gun)
  return gun
}

// The overlay lit as the world is: a sun and a sky of its own, set each frame from the world's.
function light(plugins: Plugins) {
  const T = plugins.render3d.THREE
  const { overlay, scene } = plugins.render3d
  if (!lights) {
    lights = { sun: new T.DirectionalLight(), sky: new T.HemisphereLight() }
    overlay.scene.add(lights.sun, lights.sun.target, lights.sky)
  }
  let sun: any, sky: any
  scene.traverse((o: any) => {
    if (!sun && o.isDirectionalLight) sun = o
    if (!sky && o.isHemisphereLight) sky = o
  })
  if (sun) {
    lights.sun.color.copy(sun.color)
    lights.sun.intensity = sun.intensity
    lights.sun.target.position.set(0, 0, 0)
    lights.sun.position.copy(sun.getWorldPosition(new T.Vector3()).sub(sun.target.getWorldPosition(new T.Vector3())))
  }
  if (sky) {
    lights.sky.color.copy(sky.color)
    lights.sky.groundColor.copy(sky.groundColor)
    lights.sky.intensity = sky.intensity
  }
  overlay.scene.environment = scene.environment
}

export function tick(row: Row, plugins: Plugins) {
  if (!ours) return
  const k = def(plugins.wire, row.kind)
  aiming(plugins, k)
  place(row, plugins)
}

// The camera of the row that is `mine`, the reticle in the middle of its view, and the gun before it.
function place(row: Row, plugins: Plugins) {
  const T = plugins.render3d.THREE
  const d = row.data
  const k = def(plugins.wire, row.kind)
  const camera = plugins.render3d.camera
  // a camera someone has claimed (a testbed looking elsewhere) is theirs to place
  if (!camera || plugins.render3d.claimed() !== undefined) return
  const frame = new T.Matrix4().compose(new T.Vector3().fromArray(d.pos), new T.Quaternion().setFromEuler(new T.Euler(-d.pitch, d.yaw, 0, 'YXZ')), new T.Vector3(1, 1, 1))
  camera.position.copy(new T.Vector3().fromArray(k.eye).applyMatrix4(frame))
  const [yaw, pitch] = d.aim ?? [d.yaw, d.pitch]
  const cp = Math.cos(pitch)
  const v = [Math.sin(yaw) * cp, Math.sin(pitch), Math.cos(yaw) * cp]
  camera.up.set(0, 1, 0)
  camera.lookAt(camera.position.x + v[0], camera.position.y + v[1], camera.position.z + v[2])
  camera.updateMatrixWorld(true)
  reticle.position.copy(new T.Vector3(0, 0, -1).applyMatrix4(camera.matrixWorld))
  reticle.quaternion.copy(camera.quaternion)
  reticle.scale.setScalar(2 * Math.tan((camera.fov * Math.PI) / 360))

  const g = k.shotgun
  const model = held(plugins, g.model)
  if (!model) return
  light(plugins)
  const overlay = plugins.render3d.overlay.camera
  if (overlay.near !== g.view.near || overlay.far !== g.view.far) {
    overlay.near = g.view.near
    overlay.far = g.view.far
    overlay.updateProjectionMatrix()
  }
  model.position.copy(camera.localToWorld(new T.Vector3().fromArray(g.view.at)))
  model.quaternion.copy(camera.quaternion).multiply(new T.Quaternion().setFromEuler(new T.Euler(g.view.turn[0] * DEG, g.view.turn[1] * DEG, g.view.turn[2] * DEG)))
}

export function remove(plugins: Plugins) {
  if (reticle) plugins.render3d.scene.remove(reticle)
  if (gun) plugins.render3d.overlay.scene.remove(gun)
  if (lights) plugins.render3d.overlay.scene.remove(lights.sun, lights.sun.target, lights.sky)
  if (ours) plugins.player.unbind()
  gun = undefined
  lights = undefined
  aim = [0, 0]
  aimed = undefined
}
