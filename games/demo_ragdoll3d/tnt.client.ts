// The block drawn: the loader's model its definition's `model` names, the strapped bundle of sticks
// `tnt.py` builds to its definition's `size`, standing on its row's `pos`, turned by its `yaw`, hidden
// while its row's `out` says it is gone. What it leaves when it goes off is particle3d's `boom` and
// `smoulder`, thrown by its rule (`tnt.sim.ts`).
import type { Row } from '#engine/engine.ts'
import type { Plugins } from '#engine/browser.ts'
import { def } from '#plugins/loader/loader.sim.ts'

let group: any
let model: any
let name: string

export function setup(row: Row, plugins: Plugins) {
  const T = plugins.render3d.THREE
  name = def(plugins.wire, row.kind).model
  model = undefined
  group = new T.Group()
  plugins.render3d.scene.add(group)
  tick(row, plugins)
}

export function tick(row: Row, plugins: Plugins) {
  if (!model) {
    if (plugins.loader.ready(name)) {
      model = plugins.loader.model(name).scene
      model.traverse((o: any) => {
        if (!o.isMesh) return
        o.castShadow = true
        o.receiveShadow = true
      })
      group.add(model)
    } else void plugins.loader.load(name)
  }
  group.position.fromArray(row.data.pos)
  group.rotation.y = row.data.yaw
  group.visible = row.data.out === 0
}

export function remove(plugins: Plugins) {
  plugins.render3d.scene.remove(group)
}
