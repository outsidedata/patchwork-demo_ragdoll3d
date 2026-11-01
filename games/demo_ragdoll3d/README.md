# demo_ragdoll3d

The demo of `ragdoll3d`: three X Bots stand round a block of TNT on a checkered floor between three
ramps. Shoot them with a pump shotgun and each one goes limp as a box3d ragdoll, pushed where the shot
hit. Shoot the TNT and it blows up, throwing every body near it, and you, through the air. Drop or
throw lit sticks of dynamite, which bounce and roll as box3d bodies until their fuse burns down and
they go off.

## Controls

| | keyboard and mouse | pad |
|---|---|---|
| walk | W A S D or the arrows | left stick |
| aim | the mouse (click the page to take it) | right stick |
| fire the shotgun | left button | right bumper |
| drop a stick of dynamite | G | X |
| throw a stick of dynamite | right button | Y |

## Playing it

`yarn dev`, then `http://localhost:5173/games/demo_ragdoll3d/index.html`.

`dev.html` beside it is the testbed: the same game with a panel for the TNT's and the dynamite's
blast, the dynamite's fuse and throw, your walk and how a blast throws you, the shotgun, how long a
body lies, the ragdoll's joints, and the render3d settings.

Against its server: `yarn serve demo_ragdoll3d`, then `/games/demo_ragdoll3d/client.html`.

## Remaking the art

`yarn bake demo_ragdoll3d` (`assets/demo_ragdoll3d.bake.ts`) writes:

- `checker-1024.webp`, the floor's checkerboard, drawn from nothing;
- `shotgun.glb`, from `shotgun.py` in Blender, with the library's cc0-textures sets `Wood066` and
  `Metal010`;
- `tnt.glb` and `dynamite.glb`, from `tnt.py` and `dynamite.py` in Blender, sized from the block's
  definition and the stick's box3d body;
- `farmer.glb` and the rig's table in `farmer.rig.json`, the library's X Bot
  (`characters/xbot/xbot.fbx`) with every clip of the rig baked on by anim's export.

`fx.png` and `fx.json`, the particles' sheet, are copied from demo_audio.

## Credit

The X Bot is Mixamo's. The wood and steel maps are cc0-textures.com's (ambientCG), CC0.
