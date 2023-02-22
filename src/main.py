from pyge.application import Application
from pyge.rendering import Mesh, VertexFormat, Shader, Texture2D, Sampler

import math, pygame
import numpy as np
from OpenGL.GL import *

from pygame.event import Event

from pyge.vmath import Matrix4, Vector3, Transform, Quaternion

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        self.snake_body_mesh = Mesh.from_wavefront('assets/snake_body.obj')
        self.snake_tail_mesh = Mesh.from_wavefront('assets/snake_tail.obj')
        self.snake_head_mesh = Mesh.from_wavefront('assets/snake_head.obj')

        self.shader = Shader()
        self.shader.add_shader("""
        #version 330 core
        layout (location=0) in vec3 vPos;
        layout (location=1) in vec3 vNrm;
        layout (location=2) in vec2 vTex;

        uniform mat4 uProj;
        uniform mat4 uView;
        uniform mat4 uModel;

        out vec2 vUV;
        out vec3 vNorm;
        out vec3 vPosi;

        void main() {
            mat4 vm = uView * uModel;
            vec4 pos = vm * vec4(vPos, 1.0);
            gl_Position = uProj * pos;
            vUV = vTex;
            vPosi = pos.xyz;
            vNorm = normalize(vm * vec4(vNrm, 0.0)).xyz;
        }
        """, GL_VERTEX_SHADER)

        self.shader.add_shader("""
        #version 330 core
        out vec4 fragColor;

        uniform sampler2D tex;

        in vec2 vUV;
        in vec3 vNorm;
        in vec3 vPosi;

        void main() {
            fragColor = texture(tex, vUV);
        }
        """, GL_FRAGMENT_SHADER)
        self.shader.link()

        self.snake_tex = Texture2D.from_image_file('assets/snake.png')

        self.sample = Sampler()
        self.sample.filter()
        self.sample.wrap(GL_REPEAT, GL_REPEAT)

        self.camera = Transform(translation=Vector3(0.0, 16.0, 25.0), rotation=Quaternion.from_angle_axis(-0.5, Vector3(1, 0, 0)))

        self.t = 0

        self.snake_body = []
        self.snake_head = Transform()
        self.snake_axis = 0
        self.snake_gap = 15
        self.position_history = []

        self.create_snake(15)

    def create_snake(self, size: int = 1):
        for i in range(size+1): # + tail
            xform = Transform(translation=Vector3(0.0, 0.0, 0.0))
            self.snake_body.append(xform)

    def on_event(self, event: Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
            self.snake_axis = 1
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
            self.snake_axis = -1
        else:
            self.snake_axis = 0

    def on_update(self, dt):
        self.t += dt

        self.snake_head.translation += self.snake_head.rotation.transform_vector(Vector3(1, 0, 0)) * 4.0 * dt
        self.snake_head.rotation *= Quaternion.from_angle_axis(self.snake_axis * 3.0 * dt, Vector3(0, 1, 0))

        self.position_history.insert(0, self.snake_head.translation.copy())
        i = 0
        for xform in self.snake_body:
            point = self.position_history[min(i * self.snake_gap, len(self.position_history)-1)]
            move_dir = point - xform.translation
            xform.translation += move_dir * 4.0 * dt
            xform.rotation = Quaternion.from_look_rotation(move_dir.normalize(), Vector3(0, 1, 0))
            i += 1

    def on_draw(self):
        glClearColor(0.0, 0.1, 0.35, 1.0)
        glClearDepth(1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        view = self.camera.to_matrix4().inverse()
        proj = Matrix4.from_perspective(math.pi / 4, self.display.get_width() / self.display.get_height(), 0.01, 10000.0)

        self.draw_snake(view, proj)

    def draw_snake(self, view: Matrix4, proj: Matrix4):
        self.shader.use()
        self.shader.set_uniform('uView', *view.raw)
        self.shader.set_uniform('uProj', *proj.raw)
        self.shader.set_uniform('tex', 0)

        self.snake_tex.bind(0)
        self.sample.bind(0)

        i = 0
        for xform in self.snake_body:
            model = xform.to_matrix4()
            self.shader.set_uniform('uModel', *model.raw)

            if i == 0:
                self.snake_head_mesh.draw()
            elif i == len(self.snake_body)-1:
                self.snake_tail_mesh.draw()
            else:
                self.snake_body_mesh.draw()

            i += 1


if __name__ == '__main__':
    App().run()
