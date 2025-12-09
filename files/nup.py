from enum import Enum

from .dds import DdsTexture
from .nu import *
from .read import *


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


class NuObject:
    SIZE = 0x70

    def __init__(self, data, body, vertex_bufs):
        geom_offset = read_u32(data, 0x0C)
        self.geom = NuGeom(
            body[geom_offset : geom_offset + NuGeom.SIZE], body, vertex_bufs
        )


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


def read_vertices(i, vertex_data_offset, body):
    vertex_hdr_offset = vertex_data_offset + 0x10 + i * 0x0C

    size = read_u32(body, vertex_hdr_offset)
    buf_offset = read_u32(body, vertex_hdr_offset + 0x08)

    buf_offset = vertex_data_offset + buf_offset

    return body[buf_offset : buf_offset + size]
