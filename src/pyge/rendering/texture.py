from typing import List
from OpenGL.GL import *

import numpy as np
import numpy.typing as npt

from PIL import Image

class Sampler:
    def __init__(self):
        self.id = glGenSamplers(1)
        glSamplerParameterf(self.id, GL_TEXTURE_MAX_ANISOTROPY, 16.0)
    
    def wrap(self, s: GLenum, t: GLenum=None, r: GLenum=None):
        glSamplerParameteri(self.id, GL_TEXTURE_WRAP_S, s)
        if t: glSamplerParameteri(self.id, GL_TEXTURE_WRAP_T, t)
        if r: glSamplerParameteri(self.id, GL_TEXTURE_WRAP_R, r)
    
    def filter(self, min_filter: GLenum=GL_LINEAR_MIPMAP_LINEAR, mag_filter: GLenum=GL_LINEAR):
        glSamplerParameteri(self.id, GL_TEXTURE_MIN_FILTER, min_filter)
        glSamplerParameteri(self.id, GL_TEXTURE_MAG_FILTER, mag_filter)
    
    def bind(self, unit: int=0):
        glBindSampler(unit, self.id)


class Texture:
    def __init__(self, dimensions: int, target: GLenum, internalFormat: GLenum):
        self.dimensions = dimensions
        self.target = target
        self.internalFormat = internalFormat

        self.id = GLuint()
        glCreateTextures(target, 1, self.id)

        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        self.size = [0] * dimensions

    def discard(self):
        glDeleteTextures(1, self.id)
    
    def bind(self, unit: int):
        glBindTextureUnit(unit, self.id)

    def generate_mipmaps(self):
        glGenerateTextureMipmap(self.id)

    def setup(self):
        pass

    def update(self, data: List, format: GLenum, type: GLenum):
        pass


class Texture1D(Texture):
    def __init__(self, size: int, internalFormat: GLenum):
        super().__init__(1, GL_TEXTURE_1D, internalFormat)
        self.size[0] = size
        self.setup()
    
    def setup(self):
        glTextureStorage1D(self.id, 1, self.internalFormat, self.size[0])

    def update(self, data: npt.NDArray, format: GLenum, type: GLenum):
        glTextureSubImage1D(self.id, 0, 0, self.size[0], format, type, data)


class Texture2D(Texture):
    def __init__(self, width: int, height: int, internalFormat: GLenum):
        super().__init__(2, GL_TEXTURE_2D, internalFormat)
        self.size[0] = width
        self.size[1] = height
        self.setup()
    
    def setup(self):
        glTextureStorage2D(self.id, 1, self.internalFormat, self.size[0], self.size[1])

    def update(self, data: npt.NDArray, format: GLenum, type: GLenum):
        glTextureSubImage2D(self.id, 0, 0, 0, self.size[0], self.size[1], format, type, data)

    def update_subregion(self, data: npt.NDArray, x: int, y: int, width: int, height: int, format: GLenum, type: GLenum):
        glTextureSubImage2D(self.id, 0, x, y, width, height, format, type, data)
    
    @staticmethod
    def from_image_file(file_path: str):
        img = Image.open(file_path).transpose(Image.FLIP_TOP_BOTTOM).convert('RGBA')
        img_data = np.array(img, dtype=np.uint8)
        
        tex = Texture2D(img.size[0], img.size[1], GL_RGBA8)
        tex.update(img_data, GL_RGBA, GL_UNSIGNED_BYTE)
        tex.generate_mipmaps()

        return tex


class Texture3D(Texture):
    def __init__(self, width: int, height: int, depth: int, internalFormat: GLenum):
        super().__init__(3, GL_TEXTURE_3D, internalFormat)
        self.size[0] = width
        self.size[1] = height
        self.size[2] = depth
        self.setup()
    
    def setup(self):
        glTextureStorage3D(self.id, 1, self.internalFormat, self.size[0], self.size[1], self.size[2])

    def update(self, data: npt.NDArray, format: GLenum, type: GLenum):
        glTextureSubImage3D(self.id, 0, 0, 0, 0, self.size[0], self.size[1], self.size[2], format, type, data)


class TextureCubeMap(Texture):
    POSITIVE_X = 0
    NEGATIVE_X = 1
    POSITIVE_Y = 2
    NEGATIVE_Y = 3
    POSITIVE_Z = 4
    NEGATIVE_Z = 5
    DEFAULT_MIPS = 6

    def __init__(self, width: int, height: int, internalFormat: GLenum, levels: int = 1):
        super().__init__(2, GL_TEXTURE_CUBE_MAP, internalFormat)
        self.size[0] = width
        self.size[1] = height
        self.levels = levels
        self.setup()
    
    def setup(self):
        glTextureStorage2D(self.id, self.levels, self.internalFormat, self.size[0], self.size[1])

    def update(self, data: npt.NDArray, format: GLenum, type: GLenum):
        """For cubemaps this will only update POSITIVE_X!"""
        self.update_face(0, data, format, type)

    def update_face(self, face: int, data: npt.NDArray, format: GLenum, type: GLenum):
        glTextureSubImage3D(
            self.id,
            0,      # only 1 level in example
            0,
            0,
            face,   # the offset to desired cubemap face, which offset goes to which face above
            self.size[0],
            self.size[1],
            1,      # depth how many faces to set, if this was 3 we'd set 3 cubemap faces at once
            format,
            type,
            data
        )

    @staticmethod
    def from_file(file_path: str):
        """Loads a cubemap from an image file in the following format:
                +------+
                |  +Y  |
                |      |
        +-------+------+------+------+
        |  -Z   |  -X  |  +Z  |  +X  |
        |       |      |      |      |
        +-------+------+------+------+
                |  -Y  |
                |      |
                +------+

        Args:
            file_path (str): Path to the image file
        """
        img = Image.open(file_path).convert('RGB')

        tw = img.width // 4
        th = img.height // 3

        def slice(indexX, indexY):
            x, y = indexX * tw, indexY * th
            area = (x, y, x+tw, y+th)
            return img.crop(area)
        
        indices = [
            (3, 1, TextureCubeMap.POSITIVE_X),
            (1, 1, TextureCubeMap.NEGATIVE_X),
            (1, 0, TextureCubeMap.POSITIVE_Y),
            (1, 2, TextureCubeMap.NEGATIVE_Y),
            (2, 1, TextureCubeMap.POSITIVE_Z),
            (0, 1, TextureCubeMap.NEGATIVE_Z)
        ]

        tex = TextureCubeMap(tw, th, GL_RGB8, TextureCubeMap.DEFAULT_MIPS)
        for x, y, face in indices:
            subimg = slice(x, y).transpose(Image.FLIP_TOP_BOTTOM)
            tex.update_face(face, np.array(subimg, dtype=np.uint8), GL_RGB, GL_UNSIGNED_BYTE)
        tex.generate_mipmaps()
        
        return tex
