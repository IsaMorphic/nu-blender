from .read import *


class DdsTexture:
    def __init__(self, data):
        self.data = data

        self.height = read_u32(data, 0x0C)
        self.width = read_u32(data, 0x10)
