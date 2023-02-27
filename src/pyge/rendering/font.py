from functools import wraps
from typing import Dict, List, Tuple

import freetype as ft
from freetype.ft_enums import *

import numpy as np
import numpy.typing as npt

import sys, math

from OpenGL.GL import *
import OpenGL.images as images

from pyge.vmath import Matrix4
from .geometry import Mesh, VertexFormat
from .texture import Texture2D, Sampler
from .shader import Shader, ShaderCache

# from PIL import Image, ImageDraw

vs = """
#version 330 core
layout (location=0) in vec3 vPos;
layout (location=1) in vec2 vTex;
layout (location=2) in vec4 vCol;

uniform mat4 uProj;
uniform mat4 uModel;

out vec2 oTex;
out vec4 oCol;

void main() {
    gl_Position = uProj * uModel * vec4(vPos, 1.0);
    oTex = vTex;
    oCol = vCol;
}
"""

fs = """
#version 330 core
out vec4 fragColor;

uniform sampler2D uFont;

in vec2 oTex;
in vec4 oCol;

const float smoothing = 1.0/16.0;

void main() {
    float distance = texture(uFont, oTex).r;
    float alpha = smoothstep(0.5 - smoothing, 0.5 + smoothing, distance);
    if (alpha <= 0.001) discard;
    fragColor = vec4(alpha) * oCol;
}
"""

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
        self.data = np.zeros((height, width), dtype=np.uint8)
        self.width = width
        self.height = height
    
    def blit(self, x: int, y: int, data: npt.NDArray, data_width: int, data_height: int):
        for dy in range(data_height):
            for dx in range(data_width):
                nx = x + dx; ny = y + dy
                if dx < data_width and dy < data_height and nx < self.width and ny < self.height:
                    self.data[ny, nx] = data[dx, dy]

class Font:
    def __init__(self, font_file_path: str, sdf_spread: int=16, atlas_size: int=2048):
        self.default_height = 80
        self.face = ft.Face(font_file_path)
        self.face.set_pixel_sizes(0, self.default_height)
        self.characters: Dict[str, Character] = {}
        self.character_uvs: Dict[str, Tuple[float, float, float, float]] = {}
        self.spread = int(sdf_spread)
        self.padding = int(self.spread * 1.5)

        self._rects = []

        chars = get_all_chars('cp1252')
        print(f'Processing {len(chars)} chars.')

        self.line_height = 0
        for char in chars:
            char_obj = self._generate_single_char(char)
            if not char_obj: continue
            
            self.line_height = max(self.line_height, char_obj.size[1])
            self.characters[char_obj.char] = char_obj
        self.line_height += 5

        self._pack(atlas_size, atlas_size)

        # make UVs
        for char in self.characters.values():
            x, y, w, h = char.pack_rect
            uvx1 = x / atlas_size
            uvx2 = (x + w) / atlas_size
            uvy1 = y / atlas_size
            uvy2 = (y + h) / atlas_size
            
            self.character_uvs[char.char] = (uvx1, 1.0-uvy1, uvx2, 1.0-uvy2)

        # make atlas
        atlas = BasicAtlas(atlas_size, atlas_size)
        for char in self.characters.values():
            atlas.blit(char.atlas_x, char.atlas_y, char.buffer, char.size[0], char.size[1])
        
        atlas.data = np.array(np.flipud(atlas.data))

        if sdf_spread > 1.0:
            dat = self._render_sdf(atlas.data, atlas_size, atlas_size, spread=float(sdf_spread))
        else:
            dat = atlas.data

        # texture!
        self.atlas = Texture2D(atlas_size, atlas_size, GL_R8)
        self.atlas.update(dat, GL_RED, GL_UNSIGNED_BYTE)
        self.atlas.generate_mipmaps()

        self.sample = Sampler()
        self.sample.filter()
        self.sample.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)

        # mesh!
        self._mesh = Mesh(VertexFormat.from_list([
            (3, False, GL_FLOAT), # POSITION
            (2, False, GL_FLOAT), # UV
            (4, True, GL_FLOAT)   # COLOR
        ]))
        self._previous_text = ''

        # shader
        self._shader = ShaderCache.get('_font_shader')
        if not self._shader.linked:
            self._shader.add_shader(vs, GL_VERTEX_SHADER)
            self._shader.add_shader(fs, GL_FRAGMENT_SHADER)
            self._shader.link()

        # batching
        self._drawing = False
        self._vertices = []
        self._indices = []
        self._start_index = 0
        self._draw_calls = []

        # show rects [DEBUG]
        # img = Image.fromarray(dat).convert('RGB')
        # draw = ImageDraw.Draw(img)
        # for char in self.characters.values():
        #     draw.rectangle((
        #         char.pack_rect[0], char.pack_rect[1],
        #         char.pack_rect[0]+char.pack_rect[2], char.pack_rect[1]+char.pack_rect[3]
        #     ), outline='yellow')

        # img.show()

    def begin_drawing(self):
        if self._drawing: return
        self._drawing = True
        self._start_index = 0

    def end_drawing(self, proj_view: Matrix4):
        if not self._drawing: return
        self._drawing = False
        self._mesh.update(np.array(self._vertices, dtype=np.float32), np.array(self._indices, dtype=np.uint32))
        self._vertices = []
        self._indices = []

        depthEnabled = glIsEnabled(GL_DEPTH_TEST)
        blendEnabled = glIsEnabled(GL_BLEND)
        cullfaceEnabled = glIsEnabled(GL_CULL_FACE)

        if cullfaceEnabled: glDisable(GL_CULL_FACE)
        if not blendEnabled: glEnable(GL_BLEND)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self._shader.use()

        self.sample.bind(0)
        self.atlas.bind(0)
        self._shader.set_uniform('uFont', 0)
        self._shader.set_uniform('uProj', *proj_view.raw)

        for offset, count, xform, depthTest in self._draw_calls:
            if depthEnabled and not depthTest: glDisable(GL_DEPTH_TEST)

            self._shader.set_uniform('uModel', *xform.raw)
            self._mesh.draw(count=count, offset=offset)

            if depthEnabled and not depthTest: glEnable(GL_DEPTH_TEST)

        if cullfaceEnabled: glEnable(GL_CULL_FACE)
        if not blendEnabled: glDisable(GL_BLEND)

        self._draw_calls = []

    def draw_3d(
        self,
        text: str,
        transform: Matrix4=Matrix4(), 
        scale: float=1.0,
        color: Tuple[float, float, float, float]=(1, 1, 1, 1),
        align: int=0
    ):
        scl = scale * (1.0 / self.default_height)
        """Draws a 3D text to the screen

        Args:
            text (str): Text string
            transform (Matrix4): Transformation/Model matrix
            scale (float, optional): Text scale. Defaults to 1.0.
            color (Tuple[float, float, float, float], optional): Text color. Defaults to (1, 1, 1, 1) (WHITE).
            align (int, optional): Text alignment: 0 = Left, 1 = Center, 2 = Right. Defaults to LEFT(0).
        """
        if not self._drawing:
            raise Exception('Please call begin_drawing first. Then end_drawing to complete the rendering.')

        verts, inds, _ = self._generate_text_mesh(text, 0.0, 0.0, scl, color, align, True)
        self._vertices.extend(verts)
        self._indices.extend([ i + self._start_index for i in inds ])

        self._draw_calls.append((self._start_index, len(inds), transform, True))

        self._start_index += len(verts) // self._mesh.format.size

    def draw(self,
        text: str,
        x: float, y: float,
        scale: float=1.0,
        color: Tuple[float, float, float, float]=(1, 1, 1, 1),
        align: int=0
    ):
        """Draws a 2D text to the screen

        Args:
            text (str): Text string
            x (float): X coordinate
            y (float): Y coordinate
            scale (float, optional): Text scale. Defaults to 1.0.
            color (Tuple[float, float, float, float], optional): Text color. Defaults to (1, 1, 1, 1) (WHITE).
            align (int, optional): Text alignment: 0 = Left, 1 = Center, 2 = Right. Defaults to LEFT(0).
        """
        if not self._drawing:
            raise Exception('Please call begin_drawing first. Then end_drawing to complete the rendering.')

        verts, inds, _ = self._generate_text_mesh(text, x, y, scale, color, align, False)
        self._vertices.extend(verts)
        self._indices.extend([ i + self._start_index for i in inds ])

        self._draw_calls.append((self._start_index, len(inds), Matrix4(), False))

        self._start_index += len(verts) // self._mesh.format.size

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
        c.advance = math.floor(glyph.advance.x / 64)
        c.buffer = char_buff
        c.pack_rect = (0, 0, c.size[0] + self.padding * 2, c.size[1] + self.padding * 2)
        c.atlas_x = 0
        c.atlas_y = 0

        return c
    
    def _render_sdf(self, buff: npt.NDArray, buff_width: int, buff_height: int, spread: float=1.0):
        sdf_tex = Texture2D(buff_width, buff_height, GL_R8)

        sdf_shader = """
        #version 460
        layout (local_size_x=4, local_size_y=4) in;

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
            vec2 sz = vec2(gl_NumWorkGroups.xy * 4);
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

        glDispatchCompute(sdf_tex.size[0] // 4, sdf_tex.size[1] // 4, 1)
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

    def _generate_char_vertices(
        self,
        char: Character,
        char_index: int,
        x: float, y: float, scale: float,
        color: Tuple[float, float, float, float],
        start_index: int,
        flip_y: bool
    ):
        uv = self.character_uvs[char.char]

        w = char.pack_rect[2] * scale
        h = char.pack_rect[3] * scale
        bearing_gap = (char.size[1] - char.pack_rect[3]) * scale
        xpos = (x + char.bearing[0] * scale)
        ypos = (y - char.bearing[1] * scale) + bearing_gap

        uvx1, uvy1, uvx2, uvy2 = uv

        top_h = 0 if not flip_y else h
        bot_h = h if not flip_y else 0

        if flip_y:
            ypos = (y + bearing_gap)

        z = 1e-2 * (-1 if char_index % 2 == 0 else 1)
        vertices = [
            # POSITION                  # UVs                           # COLOR
            xpos,     ypos + top_h, z,  uvx1, uvy1,  color[0], color[1], color[2], color[3],
            xpos + w, ypos + top_h, z,  uvx2, uvy1,  color[0], color[1], color[2], color[3],
            xpos + w, ypos + bot_h, z,  uvx2, uvy2,  color[0], color[1], color[2], color[3],
            xpos,     ypos + bot_h, z,  uvx1, uvy2,  color[0], color[1], color[2], color[3]
        ]
        indices = [ i + start_index for i in [ 0, 1, 2, 2, 3, 0 ] ]

        return vertices, indices

    def _measure_text(self, text: str, scale: float) -> Tuple[float, float]:
        tx = 0

        for c in list(text):
            char = None
            if c not in self.characters:
                char = self.characters['?']
            else:
                char = self.characters[c]

            if c not in ['\n', '\r']:
                tx += char.advance * scale

        return tx

    def _generate_text_mesh(self, text: str, x: float, y: float, scale: float, color: Tuple[float, float, float, float], align: int, flip_y: bool):
        """Generate text mesh

        Args:
            text (str): Text
            x (float): X coordinate
            y (float): Y coordinate
            scale (float): Text scale 0.0-x
            color (Tuple[float, float, float, float]): Text color with alpha blending
            align (int): 0 = Left, 1 = Center, 2 = Right

        Returns:
            _type_: _description_
        """
        tx = x
        ty = y

        vertices = []
        indices = []
        start_offset = 0

        line_height = self.line_height * scale

        lines = text.split('\n')
        for line in lines:
            ox = 0
            match align:
                case 1: ox = self._measure_text(line, scale)/2
                case 2: ox = self._measure_text(line, scale)
                case _: ox = 0

            index = 0
            for c in list(line):
                char = None
                if c not in self.characters:
                    char = self.characters['_']
                else:
                    char = self.characters[c]
                
                if not c.isspace():
                    verts, inds = self._generate_char_vertices(char, index, tx - ox, ty, scale, color, start_offset, flip_y)
                    vertices.extend(verts)
                    indices.extend(inds)
                    start_offset += len(verts) // self._mesh.format.size

                tx += char.advance * scale
                index += 1

            tx = x
            ty += line_height

        return vertices, indices, tx
