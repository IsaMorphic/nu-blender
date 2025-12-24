from enum import Enum

from .nu import NuVec
from .read import *


class Ter:
    def __init__(self, data):
        situs_offset = read_u32(data, 0x00) * 2
        situs_count = read_u16(data, situs_offset)

        version = read_u16(data, situs_offset + 0x02)

        self.situs = []
        model_offset = 0x04
        for i in range(situs_count):
            situs_offset_i = situs_offset + 0x04 + i * 0x34

            self.situs.append(TerSitu(data, situs_offset_i, model_offset))
            model_offset += self.situs[-1].offset_to_next * 2


class TerSitu:
    model = None

    def __init__(self, data, offset, model_offset):
        self.offset_to_next = read_u32(data, offset)
        self.location = NuVec(data, offset + 0x04)
        self.type = TerType(read_u16(data, offset + 0x10))
        self.flags = read_u16(data, offset + 0x28)
        self.id = read_i16(data, offset + 0x2E)

        if self.type == TerType.NORMAL or self.type == TerType.PLATFORM:
            self.model = TerTerrain(data, model_offset)

    def __repr__(self):
        return "TerSitu(id = {}, location = {}, type = {}, model = {})".format(
            self.id, self.location, self.type, self.model
        )


class TerTerrain:
    def __init__(self, data, offset):
        self.min_x = read_f32(data, offset + 0x00)
        self.max_x = read_f32(data, offset + 0x04)

        self.min_y = read_f32(data, offset + 0x08)
        self.max_y = read_f32(data, offset + 0x0C)

        self.min_z = read_f32(data, offset + 0x10)
        self.max_z = read_f32(data, offset + 0x14)
        
        self.points = []
        for i in range(4):
            self.points.append(NuVec(data, offset + 0x18 + i * NuVec.SIZE))

    def __repr__(self):
        return "TerTerrain(points = {})".format(self.points)


class TerType(Enum):
    NORMAL = 0
    PLATFORM = 1
    WALL_SPLINE = 2
