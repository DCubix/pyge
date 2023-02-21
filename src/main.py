from pyge.application import Application
from pyge.rendering import Mesh, VertexFormat, Shader, Texture2D, Sampler

import math
import numpy as np
from OpenGL.GL import *

from pyge.vmath import Matrix4, Vector3, Transform, Quaternion

class App(Application):
    def __init__(self):
        self.setup(opengl=True)

        self.mesh = Mesh.from_wavefront('assets/monkey.obj')

        self.shader = Shader()
        self.shader.add_shader("""
        #version 330 core
        layout (location=0) in vec3 vPos;
        layout (location=1) in vec3 vNrm;
        layout (location=2) in vec2 vTex;

        uniform mat4 xform;

        out vec2 vUV;
        out vec3 vNorm;
        void main() {
            gl_Position = xform * vec4(vPos, 1.0);
            vUV = vTex;
            vNorm = normalize(vNrm);
        }
        """, GL_VERTEX_SHADER)

        self.shader.add_shader("""
        #version 330 core
        out vec4 fragColor;

        uniform sampler2D tex;

        in vec2 vUV;
        in vec3 vNorm;
        void main() {
            float nl = max(dot(vNorm, vec3(-1.0, 1.0, 1.0)), 0.0);
            fragColor = texture(tex, vUV * 3.0) * nl;
        }
        """, GL_FRAGMENT_SHADER)
        self.shader.link()

        self.tex = Texture2D.from_image_file('assets/bricks.jpg')
        self.sample = Sampler()
        self.sample.filter()
        self.sample.wrap(GL_REPEAT, GL_REPEAT)

        glEnable(GL_DEPTH_TEST)

        self.t = 0

    def on_update(self, dt):
        self.t += dt

    def on_draw(self):
        glClearColor(0.0, 0.1, 0.35, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        proj = Matrix4.from_perspective(math.pi / 4, self.display.get_width() / self.display.get_height(), 0.01, 500.0)
        tran = Transform(translation=Vector3(0, 0, -5), rotation=Quaternion.from_angle_axis(self.t, Vector3(0,1,0)))
        xform = proj * tran.to_matrix4()

        self.tex.bind(0)
        self.sample.bind(0)

        self.shader.use()
        self.shader.set_uniform('tex', 0)
        self.shader.set_uniform('xform', *xform.raw)

        self.mesh.draw()


if __name__ == '__main__':
    App().run()
