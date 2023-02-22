from typing import List
from pyge.application import Application
from pyge.rendering import Mesh, Shader, Texture2D, Sampler

import math, pygame, random
import numpy as np
from OpenGL.GL import *

from pygame.event import Event

from pyge.vmath import Matrix4, Vector3, Transform, Quaternion

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        self.snake_body_mesh = Mesh.from_wavefront('assets/snake_body.obj')['mesh']
        self.snake_tail_mesh = Mesh.from_wavefront('assets/snake_tail.obj')['mesh']
        self.snake_head_mesh = Mesh.from_wavefront('assets/snake_head.obj')['mesh']

        self.apple_mesh = Mesh.from_wavefront('assets/apple.obj')['mesh']

        self.level_meshes = Mesh.from_wavefront('assets/level.obj')
        print(self.level_meshes.keys())

        self.snake_tex = Texture2D.from_image_file('assets/snake.png')
        self.apple_tex = Texture2D.from_image_file('assets/apple.png')
        self.level_tex = Texture2D.from_image_file('assets/grass.png')

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

        const vec3 lightDir = vec3(1.0, 1.0, 1.0);

        void main() {
            vec3 V = normalize(-vPosi);
            vec3 R = normalize(reflect(lightDir, vNorm));

            float nl = clamp(dot(vNorm, lightDir), 0.0, 1.0);
            float rim = 1.0 - clamp(dot(vNorm, V), 0.0, 1.0);
            rim = smoothstep(0.5, 1.0, rim);

            float spec = max(dot(R, -V), 0.0);
            float specTerm = pow(spec, 12.0);

            // toon shading
            float intensity = 0.6 * nl;// + 0.4 * spec;
            if (intensity > 0.9) {
                intensity = 1.2;
            }
            else if (intensity > 0.5) {
                intensity = 0.7;
            }
            else {
                intensity = 0.4;
            }

            vec4 tcol = texture(tex, vUV);
            vec3 diffuse = (tcol.rgb + tcol.rgb * rim + vec3(tcol.r * specTerm * 0.7)) * intensity;

            if (tcol.a <= 0.5) discard;

            fragColor = vec4(diffuse, 1.0);
        }
        """, GL_FRAGMENT_SHADER)
        self.shader.link()

        self.sample = Sampler()
        self.sample.filter()
        self.sample.wrap(GL_REPEAT, GL_REPEAT)

        ### Game Related
        self.camera = Transform(translation=Vector3(0.0, 16.0, 25.0), rotation=Quaternion.from_angle_axis(-0.5, Vector3(1, 0, 0)))
        self.ground = Transform(translation=Vector3(0.0, -2.1, 0.0), scale=Vector3(2.0, 2.0, 2.0))

        self.t = 0

        self.snake_body = []
        self.snake_head = Transform()
        self.snake_axis = 0
        self.snake_gap = 14
        self.snake_speed = 3.0
        self.position_history = []

        self.apples: List[Transform] = []

        self.create_snake()

        self.spawn_apple()
        self.spawn_apple()
        self.spawn_apple()

    def create_snake(self, size: int = 1):
        for _ in range(size+1): # + tail
            xform = Transform(translation=Vector3(0.0, 0.0, 0.0))
            self.snake_body.append(xform)

    def spawn_apple(self):
        rx = random.uniform(-10, 10)
        ry = random.uniform(-10, 10)
        self.apples.append(
            Transform(
                translation=Vector3(rx, 0, ry),
                rotation=Quaternion.from_angle_axis(random.uniform(-math.pi, math.pi), Vector3(0, 1, 0))
            )
        )

    def on_event(self, event: Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
            self.snake_axis = 1
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
            self.snake_axis = -1
        else:
            self.snake_axis = 0

    def on_update(self, dt):
        self.t += dt

        self.snake_head.translation += self.snake_head.rotation.transform_vector(Vector3(1, 0, 0)) * self.snake_speed * dt
        self.snake_head.rotation *= Quaternion.from_angle_axis(self.snake_axis * 3.0 * dt, Vector3(0, 1, 0))

        self.position_history.insert(0, self.snake_head.translation.copy())
        i = 0
        for xform in self.snake_body:
            point = self.position_history[min(i * self.snake_gap, len(self.position_history)-1)]
            move_dir = point - xform.translation
            xform.translation += move_dir * self.snake_speed * dt
            xform.rotation = Quaternion.from_look_rotation(move_dir.normalize(), Vector3(0, 1, 0))
            i += 1

        # rotate apples
        for xform in self.apples:
            xform.rotation *= Quaternion.from_angle_axis(3.0 * dt, Vector3(0, 1, 0))

        # check for snake head collision with apples
        for apple in self.apples:
            dist = (apple.translation - self.snake_head.translation).length()
            if dist <= 0.6:
                self.apples.remove(apple)
                # grow snake
                self.snake_body.append(self.snake_body[-1].copy())
                self.spawn_apple()
                break


    def on_draw(self):
        glClearColor(0.0, 0.1, 0.35, 1.0)
        glClearDepth(1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        view = self.camera.to_matrix4().inverse()
        proj = Matrix4.from_perspective(math.pi / 4, self.display.get_width() / self.display.get_height(), 0.01, 10000.0)

        self.draw_level(view, proj)
        self.draw_snake(view, proj)
        self.draw_apples(view, proj)

    def draw_level(self, view: Matrix4, proj: Matrix4):
        self.shader.use()
        self.shader.set_uniform('uView', *view.raw)
        self.shader.set_uniform('uProj', *proj.raw)
        self.shader.set_uniform('tex', 0)

        self.level_tex.bind(0)
        self.sample.bind(0)

        for mesh in self.level_meshes.values():
            self.shader.set_uniform('uModel', *self.ground.to_matrix4().raw)
            mesh.draw()

    def draw_apples(self, view: Matrix4, proj: Matrix4):
        self.shader.use()
        self.shader.set_uniform('uView', *view.raw)
        self.shader.set_uniform('uProj', *proj.raw)
        self.shader.set_uniform('tex', 0)

        self.apple_tex.bind(0)
        self.sample.bind(0)

        for xform in self.apples:
            model = xform.to_matrix4()
            self.shader.set_uniform('uModel', *model.raw)
            self.apple_mesh.draw()

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
