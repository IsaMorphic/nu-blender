from enum import Enum

from .read import *


class NuPlatform(Enum):
    PC = 1
    XBOX = 2


class NuTextureType(Enum):
    DXT1 = 0x0C
    DXT5 = 0x0F
    DDS = 0x0E


class NuTextureHeader:
    SIZE = 0x14

    def __init__(self, data, offset):
        self.width = read_u32(data, offset + 0x00)
        self.height = read_u32(data, offset + 0x04)
        self.levels = read_u32(data, offset + 0x08)
        self.type = NuTextureType(read_u32(data, offset + 0x0C))
        self.data_offset = read_u32(data, offset + 0x10)


class NuAlphaMode(Enum):
    NONE = 0
    MODE1 = 1
    MODE2 = 2
    MODE3 = 3
    MODE5 = 5
    MODE7 = 7
    MODE10 = 10


class NuAlphaTest(Enum):
    NONE = 0
    LESS_EQUAL = 3
    GREATER_EQUAL = 5


class NuMaterial:
    PLATFORM_OFFSETS = {
        NuPlatform.PC: 0x4,
        NuPlatform.XBOX: 0x0,
    }

    texture_idx = None

    def __init__(self, data, offset, platform):
        self.attributes = read_u32(
            data, offset + 0x3C + NuMaterial.PLATFORM_OFFSETS[platform]
        )

        self.diffuse = NuColour3(
            data, offset + 0x50 + NuMaterial.PLATFORM_OFFSETS[platform]
        )

        # This alpha value isn't used in rendering. It can hint as to the alpha
        # values in vertex data, however.
        self.alpha = read_f32(
            data, offset + 0x70 + NuMaterial.PLATFORM_OFFSETS[platform]
        )

        texture_idx = read_i16(
            data, offset + 0x74 + NuMaterial.PLATFORM_OFFSETS[platform]
        )
        if texture_idx != -1:
            self.texture_idx = texture_idx & 0x7FFF

        self.effect_id = read_u8(data, offset + 0x9D)

    def alpha_mode(self):
        return NuAlphaMode(self.attributes & 0xF)

    def alpha_test(self):
        return NuAlphaTest((self.attributes & 0x700000) >> 20)

    def alpha_ref(self):
        return (self.attributes & 0x7F800000) >> 23

    def colour(self):
        return (self.attributes & 0x40000) >> 18

    def lighting(self):
        return (self.attributes & 0x30000) >> 16


class NuGeom:
    SIZE = 0x48

    next = None

    def __init__(self, data, offset, vertex_bufs):
        next_offset = read_u32(data, offset)
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


class NuTexType(Enum):
    DXT1 = 0x0C
    DXT5 = 0x0F


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

        self.uv = (
            read_f32(data, offset + 0x1C),
            read_f32(data, offset + 0x20),
        )


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


class NuAnimData:
    def __init__(self, data, offset, header):
        self.length = read_f32(data, offset)

        chunks_count = read_i32(data, offset + 0x08)
        chunks_offset = read_u32(data, offset + 0x0C)

        self.chunks = []
        for i in range(chunks_count):
            chunks_offset_i = read_u32(data, chunks_offset + i * 0x04)
            if chunks_offset_i != 0:
                self.chunks.append(NuAnimDataChunk(data, chunks_offset_i))

    def __repr__(self):
        return "NuAnimData(length = {}, chunks = {})".format(self.length, self.chunks)


class NuAnimDataChunk:
    def __init__(self, data, offset):
        nodes_count = read_i32(data, offset)

        keys_offset = read_u32(data, offset + 0x0C)
        curves_offset = read_u32(data, offset + 0x10)

        curvesets_offset = read_u32(data, offset + 0x08)
        self.curvesets = []
        if curvesets_offset != 0:
            for i in range(nodes_count):
                curvesets_offset_i = read_u32(data, curvesets_offset + i * 0x04)
                if curvesets_offset_i != 0:
                    self.curvesets.append(
                        NuAnimCurveSet(
                            data, curvesets_offset_i, keys_offset, curves_offset
                        )
                    )

    def __repr__(self):
        return "NuAnimDataChunk({})".format(self.curvesets)


class NuAnimCurveSet:
    def __init__(self, data, offset, chunk_keys_offset, chunk_curves_offset):
        self.flags = read_u32(data, offset)
        self.has_rotation = (self.flags & 0x01) != 0
        self.has_scale = (self.flags & 0x08) != 0

        constants_offset = read_u32(data, offset + 0x04)
        curves_offset = read_u32(data, offset + 0x08)
        curves_count = read_i32(data, offset + 0x0C)

        assert curves_count == 9, "expecting exactly 9 animation components"

        self.constants = {}
        self.curves = {}

        next_curve = 0
        next_key = 0
        for i in range(curves_count):
            component = NuAnimComponent(i)

            if not self.has_rotation and (
                component == NuAnimComponent.X_ROTATION
                or component == NuAnimComponent.Y_ROTATION
                or component == NuAnimComponent.Z_ROTATION
            ):
                continue

            if not self.has_scale and (
                component == NuAnimComponent.X_SCALE
                or component == NuAnimComponent.Y_SCALE
                or component == NuAnimComponent.Z_SCALE
            ):
                continue

            constants_offset_i = constants_offset + i * 0x04

            constant = read_f32(data, constants_offset_i)
            if constant == 3.4028234663852886e38:
                chunk_curves_offset_next = (
                    chunk_curves_offset + next_curve * NuAnimCurve.SIZE
                )
                next_curve += 1

                chunk_keys_offset_next = chunk_keys_offset + next_key * NuAnimKey.SIZE

                self.curves[component] = NuAnimCurve(
                    data, chunk_curves_offset_next, chunk_keys_offset_next
                )

                next_key += len(self.curves[component].keys)
            else:
                self.constants[component] = constant

                if curves_offset != 0:
                    curves_offset_i = read_u32(data, curves_offset + i * 0x04)

                    if curves_offset_i != 0:
                        self.curves[component] = NuAnimCurve(
                            data, curves_offset_i, None
                        )

    def __repr__(self):
        return "NuAnimCurveSet(flags = 0b{:08b}, curves = {}, constants = {})".format(
            self.flags, self.curves, self.constants
        )


class NuAnimCurve:
    SIZE = 0x10

    def __init__(self, data, offset, chunk_keys_offset):
        self.mask = read_u32(data, offset)

        keys_offset = read_u32(data, offset + 0x04)
        keys_count = read_i32(data, offset + 0x08)

        flags = read_u32(data, offset + 0x0C)

        keys_offset_to_read = None
        if chunk_keys_offset:
            keys_offset_to_read = chunk_keys_offset
        elif keys_offset != 0:
            keys_offset_to_read = keys_offset

        self.keys = []
        if keys_offset_to_read is not None:
            for i in range(keys_count):
                keys_offset_i = keys_offset_to_read + i * NuAnimKey.SIZE

                self.keys.append(NuAnimKey(data, keys_offset_i))

    def __repr__(self):
        return "NuAnimCurve(mask = 0b{:032b}, keys = {})".format(self.mask, self.keys)


class NuAnimKey:
    SIZE = 0x10

    def __init__(self, data, offset):
        self.time = read_f32(data, offset)
        self.delta_time = read_f32(data, offset + 0x04)
        self.c = read_f32(data, offset + 0x08)
        self.d = read_f32(data, offset + 0x0C)

    def __repr__(self):
        return "NuAnimKey(time = {}, delta_time = {}, c = {}, d = {})".format(
            self.time, self.delta_time, self.c, self.d
        )


class NuAnimComponent(Enum):
    X_TRANSLATION = 0
    Y_TRANSLATION = 1
    Z_TRANSLATION = 2
    X_ROTATION = 3
    Y_ROTATION = 4
    Z_ROTATION = 5
    X_SCALE = 6
    Y_SCALE = 7
    Z_SCALE = 8
