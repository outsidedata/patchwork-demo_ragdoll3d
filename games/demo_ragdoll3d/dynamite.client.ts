// A stick of dynamite drawn: the loader's model its definition's `model` names, built along +Y round its
// middle as box3d's cylinder is (`dynamite.py`), put where its row's `pos` and `rot` say; and its fuse,
// a cord of the definition's `fuse.radius` and `fuse.colour` standing straight out of its +Y end from
// `fuse.root` metres past it, as long as the fuse not yet burnt: `fuse.length` times `left` over
// `fuse.burn`, so the cord shortens as the spark (particle3d's `fuse`, thrown by the rule,
// `dynamite.sim.ts`) runs down it.
import type { Row } from '#engine/engine.ts'
import type { Plugins } from '#engine/browser.ts'
import { def } from '#plugins/loader/loader.sim.ts'

let group: any
let cord: any
let model: any
let name: string

export function setup(row: Row, plugins: Plugins) {
  const T = plugins.render3d.THREE
  const k = def(plugins.wire, row.kind)
  const { height } = plugins.wire.scene.world!.box3d.kinds[row.kind].shapes[0].cylinder
  name = k.model
  model = undefined
  group = new T.Group()
  cord = new T.Mesh(new T.CylinderGeometry(k.fuse.radius, k.fuse.radius, 1, 8), new T.MeshStandardMaterial({ color: k.fuse.colour, roughness: 0.9 }))
  cord.castShadow = true
  cord.userData.base = height / 2 + k.fuse.root
  group.add(cord)
  plugins.render3d.scene.add(group)
  tick(row, plugins)
}

export function tick(row: Row, plugins: Plugins) {
  const k = def(plugins.wire, row.kind)
  if (!model) {
    if (plugins.loader.ready(name)) {
      model = plugins.loader.model(name).scene
      model.traverse((o: any) => { if (o.isMesh) o.castShadow = true })
      group.add(model)
    } else void plugins.loader.load(name)
  }
  group.position.fromArray(row.data.pos)
  group.quaternion.fromArray(row.data.rot)
  const length = k.fuse.length * Math.max(0, row.data.left) / k.fuse.burn
  cord.visible = length > 0
  cord.scale.y = Math.max(length, 1e-4)
  cord.position.y = cord.userData.base + length / 2
}

export function remove(plugins: Plugins) {
  plugins.render3d.scene.remove(group)
  cord.geometry.dispose()
  cord.material.dispose()
}
