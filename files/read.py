import struct


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
