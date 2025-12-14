class Texture:
    def __init__(self, data, offset, size, header):
        self.data = data[offset : offset + size]
        self.width = header.width
        self.height = header.height
        self.levels = header.levels
        self.type = header.type
