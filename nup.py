import bmesh
import bpy
from enum import Enum
import io
import mathutils
import os
from PIL import Image


from .files.nup import Nup, NuPrimType, RtlSet, RtlType


def import_nup(context, filepath):
    # Load scene files, including scene definition, lights, and configuration.
    with open(filepath, "rb") as file:
        data = file.read()
        nup = Nup(data)

    (path, filename) = os.path.split(filepath)
    (scene_name, _) = os.path.splitext(filename)

    bpy.ops.scene.new()

    scene = bpy.context.scene
    scene.name = scene_name

    for texture in nup.textures:
        image_bytes = io.BytesIO(texture.data)
        image = Image.open(image_bytes)

        image_as_png = io.BytesIO()
        image.save(image_as_png, "PNG")

        image_data = image_as_png.getvalue()

        blend_img = bpy.data.images.new("[unnamed]", texture.width, texture.height)
        blend_img.file_format = "PNG"
        blend_img.source = "FILE"

        blend_img.pack(data=image_data, data_len=len(image_data))

    for material in nup.materials:
        blend_mat = bpy.data.materials.new("[unnamed]")

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
            texture_node.image = bpy.data.images[material.texture_idx]

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

                mesh_materials.append(bpy.data.materials[geom.material_idx])

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
                            loop[uv_layer].uv[1] = -vertex.uv[1]

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

        mesh = bpy.data.meshes.new("[unnamed]")

        for material in mesh_materials:
            mesh.materials.append(material)

        blend_mesh.to_mesh(mesh)
        blend_mesh.free()

        # Create an object for each instance of this gobj.
        for instance in instances_by_obj.get(obj_idx, []):
            obj = bpy.data.objects.new("[unnamed]", mesh)

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

            obj.matrix_world = transform

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

    rtl_path = os.path.join(path, scene_name + ".rtl")
    with open(rtl_path, "rb") as file:
        data = file.read()
        rtl = RtlSet(data)

    world = bpy.data.worlds.new("World")

    for light in rtl.lights:
        # TODO: Figure out what the heck to do about lights other than point,
        # directional, and ambient.

        blend_light = None
        if light.type == RtlType.AMBIENT:
            # There's no real equivalent, so we set this as a property of the
            # scene.
            # TODO: Take it into account in the shader somehow?
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
