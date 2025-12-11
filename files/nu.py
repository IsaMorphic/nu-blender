from enum import Enum

from .read import *


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


class NuGeom:
    SIZE = 0x48

    next = None

    def __init__(self, data, offset, vertex_bufs):
        next_offset = read_u32(data, offset + 0x00)
        if next_offset != 0:
            self.next = NuGeom(data, next_offset, vertex_bufs)

        self.material_idx = read_u32(data, offset + 0x08)

        vertex_type = NuVtxType(read_u32(data, offset + 0x0C))

        vertex_buf_idx = read_i32(data, offset + 0x1C)
        vertex_buf = vertex_bufs[vertex_buf_idx - 1]

        self.vertices = []
        if vertex_type == NuVtxType.TC1:
            for i in range(len(vertex_buf) // NuVtxTc1.SIZE):
                self.vertices.append(NuVtxTc1(vertex_buf, i * NuVtxTc1.SIZE))

        prim_offset = read_u32(data, offset + 0x30)
        self.prim = NuPrim(data, prim_offset)


class NuVtxType(Enum):
    TC1 = 0x59


class NuPrim:
    SIZE = 0x50

    next = None

    def __init__(self, data, offset):
        next_offset = read_u32(data, offset + 0x00)
        if next_offset != 0:
            self.next = NuPrim(data, next_offset)

        self.type = NuPrimType(read_u32(data, offset + 0x04))

        indices_count = read_u16(data, offset + 0x08)
        indices_offset = read_u32(data, offset + 0x0C)

        self.index_buf = []
        for i in range(indices_count):
            self.index_buf.append(read_u16(data, indices_offset + i * 2))


class NuPrimType(Enum):
    POINT = 0x0
    LINE = 0x1
    TRI = 0x2
    TRISTRIP = 0x3
    NDXLINE = 0x4
    NDXTRI = 0x5
    NDXTRISTRIP = 0x6


class NuMtx:
    SIZE = 0x40

    def __init__(self, data, offset):
        self.rows = []
        for row in range(4):
            self.rows.append([])

            for col in range(4):
                i = row * 4 + col

                self.rows[row].append(read_f32(data, offset + i * 4))


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

    def __init__(self, data, offset):
        self.position = NuVec(data, offset)
        self.normal = NuVec(data, offset + 0x0C)
        self.colour = NuColour32(data, offset + 0x18)
        self.uv = [
            read_f32(data, offset + 0x1C),
            read_f32(data, offset + 0x20),
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
