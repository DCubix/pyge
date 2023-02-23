from .texture import Texture2D
from .shader import Shader
from OpenGL.GL import *

import ctypes

v_quad_shader = """
#version 450 core

uniform vec4 uOff;

out vec2 vUV;

void main() {

    switch (gl_VertexID) {
        case 0: gl_Position = vec4(uOff.xy + vec2(0.0, 0.0) * uOff.zw, 0.0, 1.0); vUV = vec2(0.0, 0.0); break;
        case 1: gl_Position = vec4(uOff.xy + vec2(1.0, 0.0) * uOff.zw, 0.0, 1.0); vUV = vec2(1.0, 0.0); break;
        case 2: gl_Position = vec4(uOff.xy + vec2(1.0, 1.0) * uOff.zw, 0.0, 1.0); vUV = vec2(1.0, 1.0); break;
        case 3: gl_Position = vec4(uOff.xy + vec2(1.0, 1.0) * uOff.zw, 0.0, 1.0); vUV = vec2(1.0, 1.0); break;
        case 4: gl_Position = vec4(uOff.xy + vec2(0.0, 1.0) * uOff.zw, 0.0, 1.0); vUV = vec2(0.0, 1.0); break;
        case 5: gl_Position = vec4(uOff.xy + vec2(0.0, 0.0) * uOff.zw, 0.0, 1.0); vUV = vec2(0.0, 0.0); break;
    }
}
"""

f_quad_shader = """
#version 450 core
out vec4 fragColor;

uniform sampler2D uTex;
in vec2 vUV;

void main() {
    fragColor = texture(uTex, vUV);
}
"""

class Utils:
    quad_shader: Shader = None

    @staticmethod
    def draw_quad(texture: Texture2D, x: float, y: float, width: float, height: float):
        if not Utils.quad_shader:
            shd = Shader()
            shd.add_shader(v_quad_shader, GL_VERTEX_SHADER)
            shd.add_shader(f_quad_shader, GL_FRAGMENT_SHADER)
            shd.link()
            Utils.quad_shader = shd

        Utils.quad_shader.use()
        texture.bind(0)
        Utils.quad_shader.set_uniform('uTex', 0)
        Utils.quad_shader.set_uniform('uOff', x, y, width, height)
        
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, ctypes.c_void_p(0))
