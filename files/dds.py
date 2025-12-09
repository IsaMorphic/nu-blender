from .read import *


class DdsTexture:
    def __init__(self, data, offset, size):
        self.data = data[offset : offset + size]

        self.height = read_u32(data, offset + 0x0C)
        self.width = read_u32(data, offset + 0x10)
