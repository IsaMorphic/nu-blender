# nu-blender
# Copyright (C) 2025 Seán de Búrca

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.

# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.

import bmesh
import bpy
from enum import Enum
import io
import mathutils
import os
from PIL import Image
import struct


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

        bsdf_node = node_tree.nodes["Principled BSDF"] or node_tree.nodes.new(
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

            output_node = node_tree.nodes["Material Output"] or node_tree.nodes.new(
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

            # TODO: Rotate the object for directional lights.
            if light.type == RtlType.POINT:
                obj.location = (light.pos.x, light.pos.z, light.pos.y)

            blend_light.color = (light.colour.r, light.colour.g, light.colour.b)

            bpy.context.collection.objects.link(obj)

    return {"FINISHED"}


class Nup:
    def __init__(self, data):
        body = data[0x40:]

        strings_offset = read_u32(data, 0x04)

        # Load textures.
        texture_hdr_offset = read_u32(data, 0x08)
        texture_data_offset = read_u32(body, texture_hdr_offset)
        texture_data_size = read_u32(body, texture_hdr_offset + 0x04)
        textures_count = read_i32(body, texture_hdr_offset + 0x08)

        self.textures = []
        for i in range(textures_count):
            texture_offset = read_u32(body, texture_hdr_offset + 0x1C + i * 0x14)

            # Texture size is not stored in the file, so we need to calculate a
            # rough size from the offset of each texture. This works because
            # textures are stored contiguously.
            if i < textures_count - 1:
                next_texture_offset = read_u32(
                    body, texture_hdr_offset + 0x1C + (i + 1) * 0x14
                )

                size_estimate = next_texture_offset - texture_offset
            else:
                size_estimate = texture_data_size - texture_offset

            offset_in_body = (
                texture_hdr_offset + 0x0C + texture_data_offset + texture_offset
            )

            self.textures.append(
                DdsTexture(body[offset_in_body : offset_in_body + size_estimate])
            )

        # Load materials.
        materials_offset = read_u32(data, 0x0C)
        materials_count = read_i32(body, materials_offset)

        self.materials = []
        for i in range(materials_count):
            material_offset = read_u32(body, materials_offset + 0x04 + i * 0x04)

            self.materials.append(NuMaterial(body, material_offset))

        # Load vertex data.
        vertex_data_offset = read_u32(data, 0x14)
        vertex_bufs_count = read_i32(body, vertex_data_offset)

        vertex_bufs = [
            read_vertices(i, vertex_data_offset, body) for i in range(vertex_bufs_count)
        ]

        scene_offset = read_u32(data, 0x18)
        instances_offset = read_u32(data, 0x1C)

        self.scene = NuScene(body[scene_offset:], body, instances_offset, vertex_bufs)


class RtlSet:
    def __init__(self, data):
        version = read_u32(data, 0x00)

        if version < 3:
            raise Exception("RTL version {} unsupported".format(version))
        elif version == 3:
            rtl_count = 64
        else:
            rtl_count = 128

        self.lights = []
        for i in range(rtl_count):
            self.lights.append(
                Rtl(data[0x04 + i * Rtl.SIZE : 0x04 + (i + 1) * Rtl.SIZE])
            )


class Rtl:
    SIZE = 0x8C

    def __init__(self, data):
        self.type = RtlType(read_u8(data, 0x58))

        if self.type == RtlType.POINT:
            self.pos = NuVec(data, 0x00)
        elif self.type == RtlType.DIRECTIONAL:
            self.dir = NuVec(data, 0x0C)

        self.colour = NuColour3(data, 0x18)


class RtlType(Enum):
    INVALID = 0
    AMBIENT = 1
    POINT = 2
    POINTFLICKER = 3
    DIRECTIONAL = 4
    CAMDIR = 5
    POINTBLEND = 6
    ANTILIGHT = 7
    JONFLICKER = 8


class NuScene:
    def __init__(self, data, body, instances_offset, vertex_bufs):
        objects_count = read_i32(data, 0x10)
        objects_offset = read_u32(data, 0x14)

        self.objects = []
        for i in range(objects_count):
            objects_offset_i = objects_offset + i * 4
            object_offset = read_u32(body, objects_offset_i)

            self.objects.append(
                NuObject(
                    body[object_offset : object_offset + NuObject.SIZE],
                    body,
                    vertex_bufs,
                )
            )

        instances_count = read_i32(data, 0x18)

        self.instances = []
        for i in range(instances_count):
            instances_offset_i = instances_offset + i * NuInstance.SIZE

            self.instances.append(
                NuInstance(
                    body[instances_offset_i : instances_offset_i + NuInstance.SIZE],
                    body,
                )
            )

        splines_count = read_i32(data, 0x28)
        splines_offset = read_u32(data, 0x2C)

        self.splines = []
        for i in range(splines_count):
            splines_offset_i = splines_offset + i * NuSpline.SIZE

            self.splines.append(NuSpline(body, splines_offset_i))


class NuMaterial:
    SIZE = 0xB4

    texture_idx = None

    def __init__(self, data, offset):
        attributes = read_u32(data, offset + 0x40)

        self.is_alpha_blended = (attributes & 0xF) != 0

        self.diffuse = NuColour3(data, offset + 0x54)

        # This alpha value isn't used in rendering. It can hint as to the alpha
        # values in vertex data, however.
        self.alpha = read_f32(data, offset + 0x74)

        texture_idx = read_i16(data, offset + 0x78)

        if texture_idx != -1:
            self.texture_idx = texture_idx & 0x7FFF


class NuObject:
    SIZE = 0x70

    def __init__(self, data, body, vertex_bufs):
        geom_offset = read_u32(data, 0x0C)
        self.geom = NuGeom(
            body[geom_offset : geom_offset + NuGeom.SIZE], body, vertex_bufs
        )


class NuGeom:
    SIZE = 0x48

    next = None

    def __init__(self, data, body, vertex_bufs):
        next_offset = read_u32(data, 0x00)
        if next_offset != 0:
            self.next = NuGeom(
                body[next_offset : next_offset + NuGeom.SIZE], body, vertex_bufs
            )

        self.material_idx = read_u32(data, 0x08)

        vertex_type = NuVtxType(read_u32(data, 0x0C))

        vertex_buf_idx = read_i32(data, 0x1C)
        vertex_buf = vertex_bufs[vertex_buf_idx - 1]

        self.vertices = []
        if vertex_type == NuVtxType.TC1:
            for i in range(len(vertex_buf) // NuVtxTc1.SIZE):
                self.vertices.append(
                    NuVtxTc1(vertex_buf[i * NuVtxTc1.SIZE : (i + 1) * NuVtxTc1.SIZE])
                )

        prim_offset = read_u32(data, 0x30)
        self.prim = NuPrim(body[prim_offset : prim_offset + NuPrim.SIZE], body)


class NuVtxType(Enum):
    TC1 = 0x59


class NuPrim:
    SIZE = 0x50

    next = None

    def __init__(self, data, body):
        next_offset = read_u32(data, 0x00)
        if next_offset != 0:
            self.next = NuPrim(body[next_offset : next_offset + NuPrim.SIZE], body)

        self.type = NuPrimType(read_u32(data, 0x04))

        indices_count = read_u16(data, 0x08)
        indices_offset = read_u32(data, 0x0C)

        self.index_buf = []
        for i in range(indices_count):
            self.index_buf.append(read_u16(body, indices_offset + i * 2))


class NuPrimType(Enum):
    POINT = 0x0
    LINE = 0x1
    TRI = 0x2
    TRISTRIP = 0x3
    NDXLINE = 0x4
    NDXTRI = 0x5
    NDXTRISTRIP = 0x6


class NuInstance:
    SIZE = 0x50

    anim = None

    def __init__(self, data, body):
        self.transform = NuMtx(data[0x00:0x40])
        self.obj_idx = read_i16(data, 0x40)

        anim_offset = read_u32(data, 0x48)
        if anim_offset != 0:
            self.anim = NuInstAnim(body[anim_offset : anim_offset + NuInstAnim.SIZE])


class NuInstAnim:
    SIZE = 0x60

    def __init__(self, data):
        self.mtx = NuMtx(data[0x00 : NuMtx.SIZE])


class NuSpline:
    SIZE = 0x0C

    def __init__(self, data, offset):
        points_count = read_i16(data, offset)

        name_offset = read_u32(data, offset + 0x04)
        self.name = read_string(data, name_offset)

        points_offset = read_u32(data, offset + 0x08)

        self.points = []
        for i in range(points_count):
            points_offset_i = points_offset + i * NuVec.SIZE

            self.points.append(NuVec(data, points_offset_i))


class NuMtx:
    SIZE = 0x40

    def __init__(self, data):
        self.rows = []
        for row in range(4):
            self.rows.append([])

            for col in range(4):
                i = row * 4 + col

                self.rows[row].append(read_f32(data, i * 4))


class NuVec:
    SIZE = 0x0C

    def __init__(self, data, offset):
        self.x = read_f32(data, offset)
        self.y = read_f32(data, offset + 0x04)
        self.z = read_f32(data, offset + 0x08)

    def __str__(self):
        return "NuVec({}, {}, {})".format(self.x, self.y, self.z)


class NuVtxTc1:
    SIZE = 0x24

    def __init__(self, data):
        self.position = NuVec(data, 0x00)
        self.normal = NuVec(data, 0x0C)
        self.colour = NuColour32(data, 0x18)
        self.uv = [
            read_f32(data, 0x1C),
            read_f32(data, 0x20),
        ]


class NuColour3:
    SIZE = 0xC

    def __init__(self, data, offset):
        self.r = read_f32(data, offset)
        self.g = read_f32(data, offset + 0x04)
        self.b = read_f32(data, offset + 0x08)


class NuColour32:
    def __init__(self, data, offset):
        # NUCOLOUR32 is stored with 8 bits per channel as a 32-bit ARGB value.
        # We can read these back in opposite order to account for endianness.
        blue = read_u8(data, offset)
        green = read_u8(data, offset + 0x01)
        red = read_u8(data, offset + 0x02)
        alpha = read_u8(data, offset + 0x03)

        self.r = red / 255.0
        self.g = green / 255.0
        self.b = blue / 255.0
        self.a = alpha / 255.0

    def __str__(self):
        return "NuColour32({}, {}, {}, {})".format(self.r, self.g, self.b, self.a)


class DdsTexture:
    def __init__(self, data):
        self.data = data

        self.height = read_u32(data, 0x0C)
        self.width = read_u32(data, 0x10)


def read_vertices(i, vertex_data_offset, body):
    vertex_hdr_offset = vertex_data_offset + 0x10 + i * 0x0C

    size = read_u32(body, vertex_hdr_offset)
    buf_offset = read_u32(body, vertex_hdr_offset + 0x08)

    buf_offset = vertex_data_offset + buf_offset

    return body[buf_offset : buf_offset + size]


def read_u32(data, offset):
    (u32,) = struct.unpack_from("<I", data, offset)
    return u32


def read_i32(data, offset):
    (i32,) = struct.unpack_from("<i", data, offset)
    return i32


def read_f32(data, offset):
    (f32,) = struct.unpack_from("<f", data, offset)
    return f32


def read_i16(data, offset):
    (i16,) = struct.unpack_from("<h", data, offset)
    return i16


def read_u16(data, offset):
    (u16,) = struct.unpack_from("<H", data, offset)
    return u16


def read_u8(data, offset):
    (u8,) = struct.unpack_from("<B", data, offset)
    return u8


def read_string(data, offset):
    str_bytes = bytearray()

    while data[offset] != 0:
        str_bytes.append(data[offset])
        offset += 1

    return str_bytes.decode("ascii")


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class NupImport(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""

    bl_idname = "import_scene.lsw1_nup"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import NUP"

    # ImportHelper mix-in class uses this.
    filename_ext = ".nup"

    filter_glob: StringProperty(
        default="*.nup",
        options={"HIDDEN"},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return import_nup(context, self.filepath)


def menu_func_import(self, context):
    self.layout.operator(NupImport.bl_idname, text="LSW1 Scene (.nup)")


def register():
    bpy.utils.register_class(NupImport)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(NupImport)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # Test call.
    bpy.ops.import_scene.lsw1_nup("INVOKE_DEFAULT")
