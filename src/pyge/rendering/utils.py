from typing import Dict, List
from .texture import Texture2D
from .shader import Shader
from OpenGL.GL import *

import ctypes

v_quad_shader = """
#version 460

uniform vec4 uOff;

out vec2 vUV;

const vec2 vPositions[6] = vec2[](
    vec2(0.0, 0.0),
    vec2(1.0, 0.0),
    vec2(1.0, 1.0),
    vec2(1.0, 1.0),
    vec2(0.0, 1.0),
    vec2(0.0, 0.0)
);

void main() {
    vec2 pos = vPositions[gl_VertexID];
    pos = uOff.xy + pos * uOff.zw;

    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
    vUV = vPositions[gl_VertexID];
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
    enabled_gl_state: List[GLenum] = []
    disabled_gl_state: List[GLenum] = []

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

    @staticmethod
    def push_enable_state(state: GLenum | List[GLenum]):
        state = state if isinstance(state, list) else [state]

        for s in state:
            if s in Utils.enabled_gl_state: continue

            enabled = glIsEnabled(s)
            if enabled: continue

            glEnable(s)

        Utils.enabled_gl_state.append(state)
    
    @staticmethod
    def pop_enable_state():
        if len(Utils.enabled_gl_state) == 0:
            return
        
        state = Utils.enabled_gl_state.pop()
        for s in state:
            glDisable(s)

    @staticmethod
    def push_disable_state(state: GLenum | List[GLenum]):
        state = state if isinstance(state, list) else [state]

        for s in state:
            if s in Utils.disabled_gl_state: continue

            disabled = not glIsEnabled(s)
            if disabled: continue

            glDisable(s)

        Utils.disabled_gl_state.append(state)
    
    @staticmethod
    def pop_disable_state():
        if len(Utils.disabled_gl_state) == 0:
            return
        
        state = Utils.disabled_gl_state.pop()
        for s in state:
            glEnable(s)

