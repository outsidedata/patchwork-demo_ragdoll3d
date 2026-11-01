// The kinds of blast and the blast.scene.json file next to this one: three victims idling round a
// block of TNT that goes off when shot, and the box3d ragdolls it leaves, on a shapes3d floor. Every number of them that never changes is its
// definition in `assets/demo_ragdoll3d.json`.
import type { Scene, Sim } from '#engine/engine.ts'
import { scenemanager } from '#plugins/scenemanager/scenemanager.sim.ts'
import { loader } from '#plugins/loader/loader.sim.ts'
import { box3d } from '#plugins/box3d/box3d.sim.ts'
import { player } from './player.sim.ts'
import { start } from './start.sim.ts'
import { victim } from './victim.sim.ts'
import { tnt } from './tnt.sim.ts'
import { floor } from './floor.sim.ts'
import { dynamite } from './dynamite.sim.ts'
import { bone, bonejoint } from '#plugins/ragdoll3d/ragdoll3d.sim.ts'
import { particle3d } from '#plugins/particle3d/particle3d.sim.ts'
import file from './blast.scene.json' with { type: 'json' }

export const sim: Sim = { scenemanager, loader, player, start, box3d, victim, tnt, dynamite, floor, ramp: floor, bone, bonejoint, particle3d }

export const scene = file as Scene
