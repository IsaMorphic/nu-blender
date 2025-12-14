"""
A Pillow loader for .dds files (S3TC-compressed aka DXTC)
Jerome Leclanche <jerome@leclan.ch>

Documentation:
  https://web.archive.org/web/20170802060935/http://oss.sgi.com/projects/ogl-sample/registry/EXT/texture_compression_s3tc.txt

The contents of this file are hereby released in the public domain (CC0)
Full text of the CC0 license:
  https://creativecommons.org/publicdomain/zero/1.0/
"""

from __future__ import annotations

import struct
from io import BytesIO
from typing import IO

from PIL import Image, ImageFile


def _decode565(bits: int) -> tuple[int, int, int]:
    a = ((bits >> 11) & 0x1F) << 3
    b = ((bits >> 5) & 0x3F) << 2
    c = (bits & 0x1F) << 3
    return a, b, c


def _c2a(a: int, b: int) -> int:
    return (2 * a + b) // 3


def _c2b(a: int, b: int) -> int:
    return (a + b) // 2


def _c3(a: int, b: int) -> int:
    return (2 * b + a) // 3


def _dxt1(data: IO[bytes], width: int, height: int) -> bytes:
    # TODO implement this function as pixel format in decode.c
    ret = bytearray(4 * width * height)

    for y in range(0, height, 4):
        for x in range(0, width, 4):
            color0, color1, bits = struct.unpack("<HHI", data.read(8))

            r0, g0, b0 = _decode565(color0)
            r1, g1, b1 = _decode565(color1)

            # Decode this block into 4x4 pixels
            for j in range(4):
                for i in range(4):
                    # get next control op and generate a pixel
                    control = bits & 3
                    bits = bits >> 2
                    if control == 0:
                        r, g, b = r0, g0, b0
                    elif control == 1:
                        r, g, b = r1, g1, b1
                    elif control == 2:
                        if color0 > color1:
                            r, g, b = _c2a(r0, r1), _c2a(g0, g1), _c2a(b0, b1)
                        else:
                            r, g, b = _c2b(r0, r1), _c2b(g0, g1), _c2b(b0, b1)
                    elif control == 3:
                        if color0 > color1:
                            r, g, b = _c3(r0, r1), _c3(g0, g1), _c3(b0, b1)
                        else:
                            r, g, b = 0, 0, 0

                    idx = 4 * ((y + j) * width + x + i)
                    ret[idx : idx + 4] = struct.pack("4B", r, g, b, 255)

    return bytes(ret)


def _dxtc_alpha(a0: int, a1: int, ac0: int, ac1: int, ai: int) -> int:
    if ai <= 12:
        ac = (ac0 >> ai) & 7
    elif ai == 15:
        ac = (ac0 >> 15) | ((ac1 << 1) & 6)
    else:
        ac = (ac1 >> (ai - 16)) & 7

    if ac == 0:
        alpha = a0
    elif ac == 1:
        alpha = a1
    elif a0 > a1:
        alpha = ((8 - ac) * a0 + (ac - 1) * a1) // 7
    elif ac == 6:
        alpha = 0
    elif ac == 7:
        alpha = 0xFF
    else:
        alpha = ((6 - ac) * a0 + (ac - 1) * a1) // 5

    return alpha


def _dxt5(data: IO[bytes], width: int, height: int) -> bytes:
    # TODO implement this function as pixel format in decode.c
    ret = bytearray(4 * width * height)

    for y in range(0, height, 4):
        for x in range(0, width, 4):
            a0, a1, ac0, ac1, c0, c1, code = struct.unpack("<2BHI2HI", data.read(16))

            r0, g0, b0 = _decode565(c0)
            r1, g1, b1 = _decode565(c1)

            for j in range(4):
                for i in range(4):
                    ai = 3 * (4 * j + i)
                    alpha = _dxtc_alpha(a0, a1, ac0, ac1, ai)

                    cc = (code >> 2 * (4 * j + i)) & 3
                    if cc == 0:
                        r, g, b = r0, g0, b0
                    elif cc == 1:
                        r, g, b = r1, g1, b1
                    elif cc == 2:
                        r, g, b = _c2a(r0, r1), _c2a(g0, g1), _c2a(b0, b1)
                    elif cc == 3:
                        r, g, b = _c3(r0, r1), _c3(g0, g1), _c3(b0, b1)

                    idx = 4 * ((y + j) * width + x + i)
                    ret[idx : idx + 4] = struct.pack("4B", r, g, b, alpha)

    return bytes(ret)


class DXT1Decoder(ImageFile.PyDecoder):

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        try:
            self.set_as_raw(_dxt1(BytesIO(buffer), self.state.xsize, self.state.ysize))
        except struct.error as e:
            msg = "Truncated DDS file"
            raise OSError(msg) from e
        return -1, 0


class DXT5Decoder(ImageFile.PyDecoder):
    _pulls_fd = True

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        try:
            self.set_as_raw(_dxt5(BytesIO(buffer), self.state.xsize, self.state.ysize))
        except struct.error as e:
            msg = "Truncated DDS file"
            raise OSError(msg) from e
        return -1, 0
