# nu-blender

A research-oriented Blender import add-on for scene files from the PC and Xbox
versions of *LEGO Star Wars: The Video Game* (`.nup` and `.nux`, respectively).

If present, the following additional files will be loaded:

* `.rtl` contains lighting data, including ambient lighting for the scene as
  well as point/directional lights and their colors.

* `.ter` contains scene collision data, including terrain meshes and splines
  representing invisible walls of infinite height (imported at `z = 0.0`).

## Scope

### Goals

* Research-quality import of visible or visualizable aspects of scene files,
  including collision data, object placement, animations, etc.
* Best-effort rendering of scene geometry, materials, and lighting.

### Non-goals

* High-fidelity material support to match in-game rendering.
* Scene interactivity.
* Editing and scene export.

## Building

Before building the add-on, make sure Blender 4.2 or above is installed. Then
follow the instructions [located here](build/README.md).

## Example: `Map_E`

### Scene (animated)

![A vibrant scene; Dexter's Diner is shown in LEGO style. The indoor diner scene is well-lit, centered on a bright neon sign with alien lettering. To the left, two red benches wiggle and rise as if being moved by The Force, only to fall moments later. A stool is flipped over onto its head, then moved in reverse to be set right once again. An automatic door to the right of the stool opens and closes, sliding up and down seamlessly. The scene feels warm and futuristic.](docs/images/map_e_anim.webp)

### Terrain

![The same scene described in the image above is shown in a drab, grey, blocky style. There is no motion. Each of the key scene elements such as the benches, stool, and door are replaced by convex approximations of their overall shape. This image represents the invisible collision geometry used by the game engine.](docs/images/map_e_terrain.webp)

## Example: `Gungan_A`

### Scene (animated)

![Dark forest with black sky. Two armored tanks hover into the scene, moving from the left and towards the right. Several fallen trees envelop a twisting path. Thick, dark green grass surrounds the lighter colored path, with patches of thinner vegetation decorating the edges. The felled foliage is made of LEGO pieces, decorated by bright green, studded leaves. Leafless brush fills the negative space. The scene evokes a tragic invasion of a natural utopia.](docs/images/gungan_a_anim.webp)

### Terrain

![The same scene described in the image above is shown in a drab, grey, blocky style. There is no motion. Each of the key scene elements such as the trees, tanks, and brush are replaced by convex approximations of their overall shape. This image represents the invisible collision geometry used by the game engine.](docs/images/gungan_a_terrain.webp)

## Example: `Vader_A`

### Scene (still)

![A dark, imposing corridor crushes the viewer. An arched, geometric doorway takes center stage, dimly lit from above. To the left and right are grey vents, behind which is a sea of red-hot, molten magma. Orange light makes its way through each vent, creating oppressive hot stripes on the dark, claustrophobic walls. A treacherous pathway with many pits and holes sits above lethal lava. The scene instills fear in its observer.](docs/images/vader_a_still.webp)

### Terrain

![The same scene described in the image above is shown in a drab, grey, blocky style. There is no motion. Each of the key scene elements such as the door, vents, and walkway are replaced by convex approximations of their overall shape. This image represents the invisible collision geometry used by the game engine.](docs/images/vader_a_terrain.webp)