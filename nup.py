import bmesh
import bpy
from enum import Enum
import io
import math
import mathutils
import os
from PIL import Image

from .files.nu import NuAnimComponent, NuPlatform, NuTextureType
from .files.nup import Nup, NuPrimType, RtlSet, RtlType
from .files.nu import NuPlatform, NuTextureType


def import_nup(context, filepath):
    (path, filename) = os.path.split(filepath)
    (scene_name, ext) = os.path.splitext(filename)

    # Detect scene format from file extension
    match ext.lower():
        case ".nup":
            platform = NuPlatform.PC
        case ".nux":
            platform = NuPlatform.XBOX

    # Load scene files, including scene definition, lights, and configuration.
    with open(filepath, "rb") as file:
        data = file.read()
        nup = Nup(data, platform)

    bpy.ops.scene.new()

    scene = bpy.context.scene
    scene.name = scene_name
    scene.render.fps = 60

    image_names = []
    for texture in nup.textures:
        match texture.type:
            case NuTextureType.DXT1:
                decoder = "DXT1"
            case NuTextureType.DXT5:
                decoder = "DXT5"
            case NuTextureType.DDS:
                decoder = None

        if decoder == None:
            image = Image.open(io.BytesIO(texture.data), formats=["DDS"])
        else:
            image = Image.frombytes(
                "RGBA", (texture.width, texture.height), texture.data, decoder
            )
        image_data = image.getdata()

        blend_img = bpy.data.images.new("Texture", texture.width, texture.height)
        blend_img.pixels = [item / 255.0 for t in image_data for item in t]

        image_names.append(blend_img.name)

    material_names = []
    for material in nup.materials:
        blend_mat = bpy.data.materials.new("Material")
        material_names.append(blend_mat.name)

        blend_mat.use_nodes = True
        node_tree = blend_mat.node_tree

        # This doesn't affect rendering, but shows up in layout mode. It can
        # serve as a hint for how it will be rendered, so setting it here.
        blend_mat.diffuse_color = (
            material.diffuse.r,
            material.diffuse.g,
            material.diffuse.b,
            material.alpha,
        )

        bsdf_node = node_tree.nodes.get("Principled BSDF") or node_tree.nodes.new(
            "ShaderNodeBsdfPrincipled"
        )

        vert_color_node = node_tree.nodes.new("ShaderNodeVertexColor")
        vert_color_node.layer_name = "Col"

        if material.texture_idx != None:
            texture_node = node_tree.nodes.new("ShaderNodeTexImage")
            texture_node.image = bpy.data.images[image_names[material.texture_idx]]

            # Multiply texture color and vertex color for the final unlighted
            # color. This is not game-accurate, but a quick approximation.
            color_mix_node = node_tree.nodes.new("ShaderNodeMixRGB")
            color_mix_node.blend_type = "MULTIPLY"

            node_tree.links.new(
                color_mix_node.outputs["Color"], bsdf_node.inputs["Base Color"]
            )

            node_tree.links.new(
                texture_node.outputs["Color"], color_mix_node.inputs["Color1"]
            )

            node_tree.links.new(
                vert_color_node.outputs["Color"], color_mix_node.inputs["Color2"]
            )

            if material.is_alpha_blended:
                # The `alpha` attribute is set, so blend the alpha channels as
                # well.
                alpha_mix_node = node_tree.nodes.new("ShaderNodeMix")
                alpha_mix_node.blend_type = "MULTIPLY"
                alpha_mix_node.data_type = "FLOAT"

                node_tree.links.new(
                    alpha_mix_node.outputs["Result"], bsdf_node.inputs["Alpha"]
                )

                node_tree.links.new(
                    texture_node.outputs["Alpha"], alpha_mix_node.inputs["A"]
                )

                node_tree.links.new(
                    vert_color_node.outputs["Alpha"], alpha_mix_node.inputs["B"]
                )

            output_node = node_tree.nodes.get("Material Output") or node_tree.nodes.new(
                "ShaderNodeOutputMaterial"
            )
            node_tree.links.new(
                bsdf_node.outputs["BSDF"], output_node.inputs["Surface"]
            )
        else:
            node_tree.links.new(
                vert_color_node.outputs["Color"], bsdf_node.inputs["Base Color"]
            )

            if material.is_alpha_blended:
                node_tree.links.new(
                    vert_color_node.outputs["Alpha"], bsdf_node.inputs["Alpha"]
                )

    action_names = []
    for anim in nup.scene.anim_data:
        if anim is None:
            action_names.append(None)
            continue

        action = bpy.data.actions.new("Anim Data")
        action_names.append(action.name)

        object_slot = action.slots.new("OBJECT", "Anim Data")

        layer = action.layers.new("Anim Data")
        strip = layer.strips.new()
        bag = strip.channelbag(object_slot, ensure=True)

        anim_length = math.floor(anim.length)
        for frame in range(anim_length):
            chunk_idx = frame // 32
            frame_in_chunk = frame - chunk_idx * 32

            if chunk_idx >= len(anim.chunks):
                continue

            # The game has runtime corrections to the coordinate system used in
            # its animations. In order to correctly replicate the effect on
            # rotations, we reconstruct the final transform for each keyframe
            # and decompose it back into its channels for Blender.
            curveset = anim.chunks[chunk_idx].curvesets[0]

            if curveset.has_rotation:
                x_rot = curveset_key_for_frame(
                    curveset, NuAnimComponent.X_ROTATION, frame_in_chunk
                )
                y_rot = curveset_key_for_frame(
                    curveset, NuAnimComponent.Y_ROTATION, frame_in_chunk
                )
                z_rot = curveset_key_for_frame(
                    curveset, NuAnimComponent.Z_ROTATION, frame_in_chunk
                )

                rotation = mathutils.Euler((x_rot, y_rot, z_rot), "XYZ")
            else:
                rotation = mathutils.Euler((0.0, 0.0, 0.0), "XYZ")

            if curveset.has_scale:
                x_scale = curveset_key_for_frame(
                    curveset, NuAnimComponent.X_SCALE, frame_in_chunk
                )
                y_scale = curveset_key_for_frame(
                    curveset, NuAnimComponent.Y_SCALE, frame_in_chunk
                )
                z_scale = curveset_key_for_frame(
                    curveset, NuAnimComponent.Z_SCALE, frame_in_chunk
                )

                scale = mathutils.Vector((x_scale, y_scale, z_scale))
            else:
                scale = mathutils.Vector((1.0, 1.0, 1.0))

            x = curveset_key_for_frame(
                curveset, NuAnimComponent.X_TRANSLATION, frame_in_chunk
            )
            y = curveset_key_for_frame(
                curveset, NuAnimComponent.Y_TRANSLATION, frame_in_chunk
            )
            z = curveset_key_for_frame(
                curveset, NuAnimComponent.Z_TRANSLATION, frame_in_chunk
            )

            transform = mathutils.Matrix.LocRotScale(
                mathutils.Vector((x, y, z)), rotation, scale
            )

            # Correct the coordinate system of the original data, as during the
            # game's runtime.
            for i in range(4):
                transform[i][2] = -transform[i][2]
            for j in range(4):
                transform[2][j] = -transform[2][j]

            # Swap the y and z axes for Blender's sake.
            transform = (
                mathutils.Matrix(
                    (
                        (1.0, 0.0, 0.0, 0.0),
                        (0.0, 0.0, 1.0, 0.0),
                        (0.0, 1.0, 0.0, 0.0),
                        (0.0, 0.0, 0.0, 1.0),
                    )
                )
                @ transform
            )

            translation, rotation, scale = transform.decompose()

            def last_key_value(curve):
                return curve.keyframe_points[-1].co[1]

            def add_keyframe_for_curve(prop, index, value):
                curve = bag.fcurves.ensure(prop, index=index)
                if len(curve.keyframe_points) == 0 or last_key_value(curve) != value:
                    curve.keyframe_points.insert(frame + 1, value)

            # Build the Blender keyframe.
            if curveset.has_rotation:
                w_curve = bag.fcurves.ensure("rotation_quaternion", index=0)
                if len(w_curve.keyframe_points) != 0:
                    # Ensure that the quaternion's direction of rotation is
                    # correct for proper interpolation.
                    x_curve = bag.fcurves.ensure("rotation_quaternion", index=1)
                    y_curve = bag.fcurves.ensure("rotation_quaternion", index=2)
                    z_curve = bag.fcurves.ensure("rotation_quaternion", index=3)

                    prev_quat = mathutils.Quaternion(
                        (
                            last_key_value(w_curve),
                            last_key_value(x_curve),
                            last_key_value(y_curve),
                            last_key_value(z_curve),
                        )
                    )

                    if rotation.dot(prev_quat) < 0:
                        rotation = -rotation

                add_keyframe_for_curve("rotation_quaternion", 0, rotation.w)
                add_keyframe_for_curve("rotation_quaternion", 1, rotation.x)
                add_keyframe_for_curve("rotation_quaternion", 2, rotation.y)
                add_keyframe_for_curve("rotation_quaternion", 3, rotation.z)

            if curveset.has_scale:
                add_keyframe_for_curve("scale", 0, scale.x)
                add_keyframe_for_curve("scale", 1, scale.y)
                add_keyframe_for_curve("scale", 2, scale.z)

            add_keyframe_for_curve("delta_location", 0, translation.x)
            add_keyframe_for_curve("delta_location", 1, translation.y)
            add_keyframe_for_curve("delta_location", 2, translation.z)

    # Group instances by their objid so that we can create a single mesh object
    # and provide it to each instance.
    instances_by_obj = {}
    for instance in nup.scene.instances:
        if instances_by_obj.get(instance.obj_idx) is None:
            instances_by_obj[instance.obj_idx] = [instance]
        else:
            instances_by_obj[instance.obj_idx].append(instance)

    # Transform NUP gobjs to Blender meshes.
    for obj_idx, obj in enumerate(nup.scene.objects):
        blend_mesh = bmesh.new()
        geom = obj.geom

        nu_mtl_idx_to_blend = {}
        mesh_materials = []

        # Iterate through geometry, adding vertices for each geom and breaking
        # each primitive into triangles, for which we add faces.
        while geom is not None:
            base_index = len(blend_mesh.verts)

            for vertex in geom.vertices:
                blend_vert = blend_mesh.verts.new(
                    (vertex.position.x, vertex.position.y, vertex.position.z)
                )
                blend_vert.normal = mathutils.Vector(
                    (vertex.normal.x, vertex.normal.y, vertex.normal.z)
                )

            blend_mesh.verts.ensure_lookup_table()

            blend_mat_idx = nu_mtl_idx_to_blend.get(geom.material_idx)
            if blend_mat_idx is None:
                blend_mat_idx = len(mesh_materials)
                nu_mtl_idx_to_blend[geom.material_idx] = blend_mat_idx

                mesh_materials.append(
                    bpy.data.materials[material_names[geom.material_idx]]
                )

            prim = geom.prim

            while prim is not None:
                if prim.type == NuPrimType.NDXTRISTRIP:
                    # Convert triangle strip to triangles and add faces.
                    should_reverse = True
                    for i in range(len(prim.index_buf) - 2):
                        # Preserve winding order. No idea if Blender cares about
                        # it.
                        if should_reverse:
                            corners = [
                                prim.index_buf[i],
                                prim.index_buf[i + 2],
                                prim.index_buf[i + 1],
                            ]
                        else:
                            corners = [
                                prim.index_buf[i],
                                prim.index_buf[i + 1],
                                prim.index_buf[i + 2],
                            ]

                        should_reverse = not should_reverse

                        corners_global = [corner + base_index for corner in corners]

                        # Skip degenerate triangles. We deliberately do this
                        # after flipping the winding.
                        if (
                            corners[0] == corners[1]
                            or corners[0] == corners[2]
                            or corners[1] == corners[2]
                        ):
                            continue

                        if (
                            blend_mesh.faces.get(
                                (
                                    blend_mesh.verts[corners_global[0]],
                                    blend_mesh.verts[corners_global[1]],
                                    blend_mesh.verts[corners_global[2]],
                                )
                            )
                            is not None
                        ):
                            continue

                        # Add a new Blender face for this triangle.
                        face = blend_mesh.faces.new(
                            (
                                blend_mesh.verts[corners_global[0]],
                                blend_mesh.verts[corners_global[1]],
                                blend_mesh.verts[corners_global[2]],
                            )
                        )

                        face.material_index = blend_mat_idx

                        uv_layer = blend_mesh.loops.layers.uv.verify()
                        color_layer = blend_mesh.loops.layers.color.verify()

                        for i, loop in enumerate(face.loops):
                            vert = corners[i]

                            vertex = geom.vertices[vert]

                            loop[uv_layer].uv[0] = vertex.uv[0]
                            loop[uv_layer].uv[1] = vertex.uv[1]

                            vert_color = vertex.colour
                            loop[color_layer] = (
                                vert_color.r,
                                vert_color.g,
                                vert_color.b,
                                vert_color.a,
                            )
                else:
                    return {"CANCELLED"}

                prim = prim.next

            geom = geom.next

        mesh = bpy.data.meshes.new("Object")

        for material in mesh_materials:
            mesh.materials.append(material)

        blend_mesh.to_mesh(mesh)
        blend_mesh.free()

        # Create an object for each instance of this gobj.
        for instance in instances_by_obj.get(obj_idx, []):
            obj = bpy.data.objects.new("Instance", mesh)

            if instance.anim is not None:
                transform = mathutils.Matrix(instance.anim.mtx.rows)
            else:
                transform = mathutils.Matrix(instance.transform.rows)

            transform.transpose()

            transform = (
                mathutils.Matrix(
                    (
                        (1.0, 0.0, 0.0, 0.0),
                        (0.0, 0.0, 1.0, 0.0),
                        (0.0, 1.0, 0.0, 0.0),
                        (0.0, 0.0, 0.0, 1.0),
                    )
                )
                @ transform
            )

            # Animations use the `rotation_quaternion` property, so we need to
            # set the object's rotation mode to match.
            obj.rotation_mode = "QUATERNION"

            obj.matrix_world = transform

            if instance.anim is not None:
                action_name = action_names[instance.anim.anim_idx]

                if action_name is not None:
                    anim_data = obj.animation_data_create()
                    action = bpy.data.actions[action_name]

                    anim_data.action = action
                    anim_data.action_slot = action.slots[0]

            bpy.context.collection.objects.link(obj)

            if not instance.is_visible:
                obj.hide_set(True)

    for spline in nup.scene.splines:
        curve = bpy.data.curves.new(spline.name, "CURVE")
        blend_spline = curve.splines.new("POLY")
        blend_spline.points.add(len(spline.points) - 1)

        for i, point in enumerate(spline.points):
            blend_spline.points[i].co = (point.x, point.z, point.y, 0.0)

        obj = bpy.data.objects.new(spline.name, curve)
        bpy.context.collection.objects.link(obj)

    # Case-insensitve file lookup for RTL
    rtl_path = None
    rtl_name = scene_name.lower() + ".rtl"
    for file_name in os.listdir(path):
        if file_name.lower() == rtl_name:
            rtl_path = os.path.join(path, file_name)
            break

    if rtl_path == None:
        return {"FINISHED"}

    with open(rtl_path, "rb") as file:
        data = file.read()
        rtl = RtlSet(data)

    # Set the world background color to approximate ambient lighting.
    world = bpy.data.worlds.new("World")
    world.use_nodes = True

    ambient_node = world.node_tree.nodes.new("ShaderNodeAttribute")
    ambient_node.attribute_name = "Ambient"
    ambient_node.attribute_type = "VIEW_LAYER"

    color_bg_node = world.node_tree.nodes.get(
        "Background"
    ) or world.node_tree.nodes.new("ShaderNodeBackground")

    world.node_tree.links.new(
        ambient_node.outputs["Color"], color_bg_node.inputs["Color"]
    )

    # We can configure the world shader to _display_ the world background as
    # black, as it is in-game, even though the lighting contribution comes from
    # the ambient color.
    display_bg_node = world.node_tree.nodes.new("ShaderNodeBackground")
    display_bg_node.inputs["Color"].default_value = (0.0, 0.0, 0.0, 0.0)

    light_node = world.node_tree.nodes.new("ShaderNodeLightPath")

    bg_selector_node = world.node_tree.nodes.new("ShaderNodeMixShader")

    world.node_tree.links.new(
        light_node.outputs["Is Camera Ray"], bg_selector_node.inputs[0]
    )

    world.node_tree.links.new(
        color_bg_node.outputs["Background"], bg_selector_node.inputs[1]
    )

    world.node_tree.links.new(
        display_bg_node.outputs["Background"], bg_selector_node.inputs[2]
    )

    output_node = world.node_tree.nodes.get(
        "World Output"
    ) or world.node_tree.nodes.new("ShaderNodeOutputWorld")

    world.node_tree.links.new(
        bg_selector_node.outputs["Shader"], output_node.inputs["Surface"]
    )

    scene.world = world

    for light in rtl.lights:
        # TODO: Figure out what the heck to do about lights other than point,
        # directional, and ambient.

        blend_light = None
        if light.type == RtlType.AMBIENT:
            # There's no real equivalent, so we set this as a property of the
            # scene.
            scene["Ambient"] = [light.colour.r, light.colour.g, light.colour.b]
        elif light.type == RtlType.POINT:
            blend_light = bpy.data.lights.new("Light", "POINT")
        elif light.type == RtlType.DIRECTIONAL:
            blend_light = bpy.data.lights.new("Light", "SUN")

        if blend_light is not None:
            obj = bpy.data.objects.new("Light", blend_light)

            if light.type == RtlType.POINT:
                obj.location = (light.pos.x, light.pos.z, light.pos.y)
            if light.type == RtlType.DIRECTIONAL:
                blend_light.use_shadow = False

                direction = light.dir
                obj.matrix_world = mathutils.Matrix(
                    (
                        (0.0, direction.x, 0.0, 0.0),
                        (0.0, direction.z, 0.0, 0.0),
                        (0.0, direction.y, 0.0, 0.0),
                        (0.0, 0.0, 0.0, 1.0),
                    )
                )

            blend_light.color = (light.colour.r, light.colour.g, light.colour.b)

            bpy.context.collection.objects.link(obj)

    return {"FINISHED"}


def curveset_key_for_frame(curveset, component, frame):
    curve = curveset.curves.get(component)
    if curve is not None:
        key_idx = curve_key_idx_for_frame(curve, frame)
        return curve.keys[key_idx].d
    else:
        return curveset.constants[component]


def curve_key_idx_for_frame(curve, frame):
    frame_mask = 1 << frame + 1
    return (curve.mask & (frame_mask - 1)).bit_count() - 1
