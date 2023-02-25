from functools import wraps
from typing import Dict, List, Tuple

import freetype as ft
from freetype.ft_enums import *

import numpy as np
import numpy.typing as npt

import sys

from OpenGL.GL import *
import OpenGL.images as images

from .texture import Texture2D
from .shader import Shader

from PIL import Image, ImageDraw

def get_all_chars(encoding) -> List[str]:
    chars = []
    for x in range(sys.maxunicode):
        u = chr(x)
        try:
            s = u.encode(encoding)
        except:
            continue
        chars.append(u)
    return chars

def map_range(val: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    norm = (val - in_min) / (in_max - in_min)
    return out_min + norm * (out_max - out_min)

class Character:
    char: str
    atlas_x: int
    atlas_y: int
    size: Tuple[int, int]
    pack_rect: Tuple[int, int, int, int]
    bearing: Tuple[int, int]
    advance: int
    buffer: npt.NDArray

class BasicAtlas:
    def __init__(self, width: int, height: int):
        self.data = np.zeros((width, height), dtype=np.uint8)
        self.width = width
        self.height = height
    
    def blit(self, x: int, y: int, data: npt.NDArray, data_width: int, data_height: int):
        for dy in range(data_height):
            for dx in range(data_width):
                nx = x + dx; ny = y + dy
                if dx < data_width and dy < data_height and nx < self.width and ny < self.height:
                    self.data[nx, ny] = data[dx, dy]

class Font:
    def __init__(self, font_file_path: str, sdf_spread: int=12, atlas_size: int=1440):
        self.face = ft.Face(font_file_path)
        self.face.set_pixel_sizes(0, 80)
        self.characters: Dict[str, Character] = {}
        self.character_uvs: Dict[str, Tuple[float, float, float, float]] = {}
        self.spread = int(sdf_spread)
        self.padding = int(self.spread * 1.5)

        self._rects = []

        chars = get_all_chars('cp1252')
        print(f'Processing {len(chars)} chars.')

        for char in chars:
            char_obj = self._generate_single_char(char)
            if not char_obj: continue
            
            self.characters[char_obj.char] = char_obj

        self._pack(atlas_size, atlas_size)

        atlas = BasicAtlas(atlas_size, atlas_size)
        for char in self.characters.values():
            atlas.blit(char.atlas_x, char.atlas_y, char.buffer, char.size[0], char.size[1])
        
        if sdf_spread > 1.0:
            dat = self._render_sdf(atlas.data.transpose(), atlas_size, atlas_size, spread=float(sdf_spread)).transpose()
        else:
            dat = atlas.data

        # show rects [DEBUG]
        # img = Image.fromarray(dat).convert('RGB')
        # draw = ImageDraw.Draw(img)
        # for char in self.characters.values():
        #     draw.rectangle((
        #         char.pack_rect[0], char.pack_rect[1],
        #         char.pack_rect[0]+char.pack_rect[2], char.pack_rect[1]+char.pack_rect[3]
        #     ), outline='yellow')

        # img.show()

    def _generate_single_char(self, char: str):
        self.face.load_char(char)

        glyph = self.face.glyph

        width = glyph.bitmap.width
        height = glyph.bitmap.rows
        if width * height <= 0: return None

        char_buff = np.array(glyph.bitmap.buffer, dtype=np.uint8).reshape((height, width)).transpose()

        c = Character()
        c.char = char
        c.size = (width, height)
        c.bearing = (glyph.bitmap_left, glyph.bitmap_top)
        c.advance = glyph.advance.x
        c.buffer = char_buff
        c.pack_rect = (0, 0, c.size[0] + self.padding * 2, c.size[1] + self.padding * 2)
        c.atlas_x = 0
        c.atlas_y = 0

        return c
    
    def _render_sdf(self, buff: npt.NDArray, buff_width: int, buff_height: int, spread: float=1.0):
        sdf_tex = Texture2D(buff_width, buff_height, GL_R8)

        sdf_shader = """
        #version 460
        layout (local_size_x=2, local_size_y=2) in;

        layout (r8, binding=0) uniform image2D uInput;
        layout (r8, binding=1) uniform image2D uOutSDF;

        uniform float spread;

        int getBit(ivec2 p) {
            ivec2 sz = imageSize(uInput);
            if (p.x < 0 || p.y < 0 || p.x >= sz.x || p.y >= sz.y) return 0;
            return imageLoad(uInput, p).r > 0.5 ? 1 : 0;
        }

        float findSignedDistance(ivec2 center, float spreadValue) {
            ivec2 sz = imageSize(uInput);
            int state = getBit(center);

            int delta = int(ceil(spreadValue));
            int minX = max(0, center.x - delta);
            int maxX = min(sz.x, center.x + delta);
            int minY = max(0, center.y - delta);
            int maxY = min(sz.y, center.y + delta);

            float minDist = float(delta * delta);
            for (int y = minY; y < maxY; y++) {
                for (int x = minX; x < maxX; x++) {
                    int pixelState = getBit(ivec2(x, y));
                    float dxSq = pow(float(center.x - x), 2.0);
                    float dySq = pow(float(center.y - y), 2.0);
                    float distSq = dxSq + dySq;
                    if (pixelState != state) {
                        minDist = min(minDist, distSq);
                    }
                }
            }

            minDist = sqrt(minDist);
            return (state == 1 ? 1 : -1) * min(minDist, spreadValue);
        }

        void main() {
            vec2 sz = vec2(gl_NumWorkGroups.xy * 2);
            vec2 pos = vec2(gl_GlobalInvocationID.xy);
            
            float centerX = floor(pos.x + 0.5);
            float centerY = floor(pos.y + 0.5);
            vec2 center = vec2(centerX, centerY);
            float dist = findSignedDistance(ivec2(center), spread);

            float alpha = (dist / spread) * 0.5 + 0.5;
            alpha = clamp(alpha, 0.0, 1.0);

            imageStore(uOutSDF, ivec2(pos), vec4(alpha));
        }
        """
        shd = Shader()
        shd.add_shader(sdf_shader, GL_COMPUTE_SHADER)
        shd.link()

        shd.use()
        
        glyph = Texture2D(buff_width, buff_height, GL_R8)
        glyph.update(buff, GL_RED, GL_UNSIGNED_BYTE)
        
        glBindImageTexture(0, glyph.id, 0, GL_FALSE, 0, GL_READ_ONLY, GL_R8)
        shd.set_uniform('uInput', 0)

        glBindImageTexture(1, sdf_tex.id, 0, GL_FALSE, 0, GL_WRITE_ONLY, GL_R8)
        shd.set_uniform('uOutSDF', 1)

        shd.set_uniform('spread', spread)

        glDispatchCompute(sdf_tex.size[0] // 2, sdf_tex.size[1] // 2, 1)
        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        imageData = images.SetupPixelRead(GL_RED, sdf_tex.size, GL_UNSIGNED_BYTE)

        buffSize = buff_width * buff_height
        glGetTextureImage(sdf_tex.id, 0, GL_RED, GL_UNSIGNED_BYTE, buffSize, imageData)

        glyph.discard()
        sdf_tex.discard()

        return imageData

    def _pack(self, width: int, height: int):
        class Rect:
            x: int
            y: int
            w: int
            h: int
            def __init__(self, x, y, w, h):
                self.x = x
                self.y = y
                self.w = w
                self.h = h
        spaces: List[Rect] = []

        def create_space(x, y, w, h):
            spaces.append(Rect(x, y, w, h))
        
        def create_rect(char: Character) -> Rect:
            _, _, cw, ch = char.pack_rect

            rec = Rect(0, 0, cw, ch)

            for i in range(len(spaces)-1, -1, -1):
                space = spaces[i]
                if rec.w > space.w or rec.h > space.h: continue

                rec.x = space.x
                rec.y = space.y

                if rec.w == space.w and rec.h == space.h:
                    last = spaces.pop()
                    if i < len(spaces): spaces[i] = last
                elif rec.w == space.w:
                    space.y += rec.h
                    space.h -= rec.h
                elif rec.h == space.h:
                    space.x += rec.w
                    space.w -= rec.w
                else:
                    # divide
                    create_space(space.x + rec.w, space.y, space.w - rec.w, rec.h)
                    space.y += rec.h
                    space.h -= rec.h
                break
            
            return rec

        create_space(0, 0, width, height)

        char_list = list(self.characters.values())
        char_list.sort(key=lambda a: a.size[1], reverse=True)

        def npot(n):
            n -= 1
            while n & n-1: n = n & n - 1
            return n << 1

        max_h = 0
        for char in char_list:
            rec = create_rect(char)
            char.atlas_x = rec.x + self.padding
            char.atlas_y = rec.y + self.padding
            char.pack_rect = (rec.x, rec.y, rec.w, rec.h)

            max_h = max(rec.y + rec.h, max_h)

        return npot(max_h)
