// The floor of blast and the ramp behind the victim, each a shapes3d plane (`world.shapes3d.kinds.floor`
// and `.ramp`), drawn by solids from its look, stood in box3d's world as a slab, and where hitscan3d's
// shots stop. `blast.sim.ts` hands this rule out under both names. It has no rule.
import type { Kind } from '#engine/engine.ts'

export const floor: Kind = {}
