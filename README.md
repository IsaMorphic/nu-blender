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
