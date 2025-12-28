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

            self.situs.append(NuSitu(data, situs_offset_i, model_offset))
            model_offset += self.situs[-1].offset_to_next * 2


class NuSitu:
    groups = None

    def __init__(self, data, offset, model_offset):
        self.offset_to_next = read_u32(data, offset)
        self.location = NuVec(data, offset + 0x04)
        self.type = TerType(read_u16(data, offset + 0x10))
        self.flags = read_u16(data, offset + 0x28)
        self.id = read_i16(data, offset + 0x2E)

        if self.type == TerType.NORMAL or self.type == TerType.PLATFORM:
            self.groups = []

            # Loop over groups until we find one with an index of -1, indicating
            # it is not a valid group.
            while True:
                index = read_i16(data, model_offset)
                if index == -1:
                    break

                self.groups.append(NuTerGroup(data, model_offset))

                model_offset += 0x14 + len(self.groups[-1].ters) * NuTer.SIZE
        elif self.type == TerType.WALL_SPLINE:
            self.spline = NuWallSpline(data, model_offset)

    def __repr__(self):
        return "NuSitu(id = {}, location = {}, type = {}, model = {})".format(
            self.id,
            self.location,
            self.type,
            (
                self.groups
                if (self.type == TerType.NORMAL or self.type == TerType.PLATFORM)
                else self.spline
            ),
        )


class NuWallSpline:
    def __init__(self, data, offset):
        points_count = read_i16(data, offset + 0x04)

        self.points = []
        for i in range(points_count):
            points_offset_i = offset + 0x08 + i * NuVec.SIZE

            self.points.append(NuVec(data, points_offset_i))

    def __repr__(self):
        return "NuWallSpline(points = {})".format(self.points)


class NuTerGroup:
    def __init__(self, data, offset):
        ter_count = read_i16(data, offset + 0x02)
        minx = read_f32(data, offset + 0x04)
        minz = read_f32(data, offset + 0x08)
        maxx = read_f32(data, offset + 0x0C)
        maxz = read_f32(data, offset + 0x10)

        self.ters = []
        for i in range(ter_count):
            ters_offset_i = offset + 0x14 + i * NuTer.SIZE
            self.ters.append(NuTer(data, ters_offset_i))

    def __repr__(self):
        return "NuTerGroup(ters = {})".format(self.ters)


class NuTer:
    SIZE = 0x64

    def __init__(self, data, offset):
        self.norms = []
        for i in range(2):
            self.norms.append(NuVec(data, offset + 0x48 + i * NuVec.SIZE))

        # An invalid second normal is used to indicate that the surface is a
        # triangle instead of a full quad.
        if self.norms[1].y > 65535.0:
            point_count = 3
        else:
            point_count = 4

        self.points = []
        for i in range(point_count):
            self.points.append(NuVec(data, offset + 0x18 + i * NuVec.SIZE))

        self.info = []
        for i in range(4):
            self.info.append(read_u8(data, offset + 0x60 + i))

    def __repr__(self):
        return "NuTer(points = {}, info = {})".format(self.points, self.info)


class TerType(Enum):
    NORMAL = 0
    PLATFORM = 1
    WALL_SPLINE = 2
