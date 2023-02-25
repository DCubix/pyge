from functools import wraps
from typing import Dict, List, Tuple

from concurrent.futures import ThreadPoolExecutor, as_completed

from matplotlib import pyplot as plt

import freetype as ft
from freetype.ft_enums import *

import numpy as np
import numpy.typing as npt

import sys, time, math

padding = 5

def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds')
        return result
    return timeit_wrapper

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
    def __init__(self, font_file_path: str, resolution: int=1024):
        self.face = ft.Face(font_file_path)
        self.face.set_pixel_sizes(0, 72)
        self.characters: Dict[str, Character] = {}

        self._rects = []

        chars = get_all_chars('cp1252')
        print(f'Processing {len(chars)} chars.')

        for char in chars:
            char_obj = self._generate_single_char(char)
            if not char_obj: continue

            self.characters[char_obj.char] = char_obj

        self._pack(resolution, resolution)

        atlas = BasicAtlas(resolution, resolution)
        for char in self.characters.values():
            atlas.blit(char.atlas_x, char.atlas_y, char.buffer, char.size[0], char.size[1])
        
        plt.imshow(atlas.data.transpose(), interpolation='nearest')
        plt.show()


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
        c.atlas_x = 0
        c.atlas_y = 0

        return c

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
        
        def create_rect(char: Character):
            cw, ch = char.size

            cw += padding
            ch += padding

            for i in range(len(spaces)-1, -1, -1):
                space = spaces[i]
                if cw > space.w or ch > space.h: continue

                char.atlas_x = space.x + padding
                char.atlas_y = space.y + padding

                if cw == space.w and ch == space.h:
                    last = spaces.pop()
                    if i < len(spaces): spaces[i] = last
                elif cw == space.w:
                    space.y += ch
                    space.h -= ch
                elif ch == space.h:
                    space.x += cw
                    space.w -= cw
                else:
                    # divide
                    create_space(space.x + cw, space.y, space.w - cw, ch)
                    space.y += ch
                    space.h -= ch
                break

        create_space(0, 0, width, height)

        char_list = list(self.characters.values())
        char_list.sort(key=lambda a: a.size[1], reverse=True)

        for char in char_list:
            create_rect(char)

Font('assets/os_bold.ttf')