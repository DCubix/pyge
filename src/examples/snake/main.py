import pyge_import

from typing import List
from apple import Apple
from pyge.application import Application
from pyge.rendering import Mesh, Shader, Texture2D, Sampler, RenderTarget, Utils, Font
from pyge.vmath import Matrix4, Vector3, Transform, Quaternion

import math, pygame, random
import numpy as np
from OpenGL.GL import *

from pygame.event import Event

lightProj = Matrix4.from_orthographic(-30, 30, -30, 30, 0.001, 600.0)

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        self.font = Font(f'{pyge_import.assets_folder}/allegro.ttf')

        self.snake_body_mesh = Mesh.from_wavefront(f'{pyge_import.assets_folder}/snake_body.obj')['mesh']
        self.snake_tail_mesh = Mesh.from_wavefront(f'{pyge_import.assets_folder}/snake_tail.obj')['mesh']
        self.snake_head_mesh = Mesh.from_wavefront(f'{pyge_import.assets_folder}/snake_head.obj')['mesh']

        self.apple_mesh = Mesh.from_wavefront(f'{pyge_import.assets_folder}/apple.obj')['mesh']

        self.level_meshes = Mesh.from_wavefront(f'{pyge_import.assets_folder}/level.obj')
        print(self.level_meshes.keys())

        self.snake_tex = Texture2D.from_image_file(f'{pyge_import.assets_folder}/snake.png')
        self.apple_tex = Texture2D.from_image_file(f'{pyge_import.assets_folder}/apple.png')
        self.level_tex = Texture2D.from_image_file(f'{pyge_import.assets_folder}/grass.png')

        self.shader = Shader()
        self.shader.add_shader_from_file(f'{pyge_import.assets_folder}/shaders/default.vert', GL_VERTEX_SHADER)
        self.shader.add_shader_from_file(f'{pyge_import.assets_folder}/shaders/default.frag', GL_FRAGMENT_SHADER)
        self.shader.link()

        self.shadow_shader = Shader()
        self.shadow_shader.add_shader_from_file(f'{pyge_import.assets_folder}/shaders/shadow.vert', GL_VERTEX_SHADER)
        self.shadow_shader.add_shader_from_file(f'{pyge_import.assets_folder}/shaders/shadow.frag', GL_FRAGMENT_SHADER)
        self.shadow_shader.link()

        self.shadow_buffer = RenderTarget(1024, 1024)
        self.shadow_buffer.add_depth_attachment()

        self.sample = Sampler()
        self.sample.filter()
        self.sample.wrap(GL_REPEAT, GL_REPEAT)

        self.shadow_sample = Sampler()
        self.shadow_sample.wrap(GL_CLAMP_TO_BORDER, GL_CLAMP_TO_BORDER)

        ### Game Related
        self.camera_pos_offset = cam_pos = Vector3(0.0, 25, 30.0)
        self.camera = Transform(translation=cam_pos, rotation=Quaternion.from_look_at(cam_pos, Vector3(0.0, 0.0, 0.0)))
        self.light = Transform(rotation=Quaternion.from_look_at(Vector3(2, 2, 2), Vector3(0.0, 0.0, 0.0)))
        self.ground = Transform(translation=Vector3(0.0, -1.3, 0.0), scale=Vector3(2.0, 2.0, 2.0))

        self.t = 0

        self.snake_body = []
        self.snake_head = Transform()
        self.snake_axis = 0
        self.snake_gap = 14
        self.snake_speed = 3.0
        self.position_history = []

        self.score = 0

        self.apples: List[Apple] = []

        self.create_snake()

        for i in range(10):
            self.spawn_apple()

    def create_snake(self, size: int = 1):
        for _ in range(size+1): # + tail
            xform = Transform(translation=Vector3(0.0, 0.0, 0.0))
            self.snake_body.append(xform)

    def spawn_apple(self):
        rx = random.uniform(-18, 18)
        ry = random.uniform(-18, 18)
        apple = Apple()
        apple.transform = Transform(
            translation=Vector3(rx, 0, ry),
            rotation=Quaternion.from_angle_axis(random.uniform(-math.pi, math.pi), Vector3(0, 1, 0)),
            scale=Vector3()
        )
        self.apples.append(apple)

    def on_event(self, event: Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
            self.snake_axis = 1
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
            self.snake_axis = -1
        else:
            self.snake_axis = 0

    def on_update(self, dt):
        self.t += dt

        # move snake head
        self.snake_head.translation += self.snake_head.rotation.transform_vector(Vector3(1, 0, 0)) * self.snake_speed * dt
        self.snake_head.rotation *= Quaternion.from_angle_axis(self.snake_axis * 3.0 * dt, Vector3(0, 1, 0))

        # camera follow snake head
        self.camera.translation = self.camera.translation.lerp(self.snake_head.translation + self.camera_pos_offset, 0.4)

        # move snake body
        self.position_history.insert(0, self.snake_head.translation.copy())
        i = 0
        for xform in self.snake_body:
            point = self.position_history[min(i * self.snake_gap, len(self.position_history)-1)]
            move_dir = point - xform.translation
            xform.translation += move_dir * self.snake_speed * dt
            xform.rotation = Quaternion.from_look_rotation(move_dir.normalize(), Vector3(0, 1, 0))
            i += 1

        # rotate apples
        for apple in self.apples:
            apple.update(dt)

        # small detail: move apples away from the body
        for apple in self.apples:
            for body in self.snake_body:
                vec = (apple.transform.translation - body.translation)
                dist = vec.length()
                if dist <= 1.25:
                    apple.transform.translation += vec * dt * 5.0

        # check for snake head collision with apples
        for apple in self.apples:
            if apple.state != Apple.IDLING: continue

            vec: Vector3 = (apple.transform.translation - self.snake_head.translation)
            dist = vec.length()

            if dist <= 0.6:
                apple.set_eaten()
                break

        for apple in self.apples:
            if apple.state == Apple.DEAD:
                self.apples.remove(apple)
                self.snake_body.append(self.snake_body[-1].copy())
                self.score += 1
                self.spawn_apple()


    def on_draw(self):
        glClearColor(0.0, 0.1, 0.35, 1.0)
        glClearDepth(1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        view = self.camera.to_matrix4().inverse()
        proj = Matrix4.from_perspective(math.pi / 5, self.display.get_width() / self.display.get_height(), 0.01, 1000.0)

        self.shadow_shader.use()
        self.draw_shadows()

        lightMatrix = lightProj * self.light.to_matrix4().inverse()

        self.shader.use()
        self.shader.set_uniform('lightDir', *self.light.transform_vector(Vector3(0, 0, 1)).raw)
        self.shader.set_uniform('uLightMatrix', *lightMatrix.raw)
        self.shader.set_uniform('shadowMap', 1)

        self.shadow_sample.bind(1)
        self.shadow_buffer.depth_attachment.bind(1)

        self.draw_scene(self.shader, view, proj)

        # aspect = self.display.get_width() / self.display.get_height()
        # Utils.draw_quad(self.shadow_buffer.depth_attachment, 0.01, -0.1, 0.8, 0.8 * aspect)

        ortho2d = Matrix4.from_orthographic(0, self.display.get_width(), self.display.get_height(), 0, -1, 1)

        self.font.begin_drawing()
        self.font.draw('Testing Some\nMultiline Text\nThis is just to test multiline\ntext and alignment!', 200.0, 150.0, scale=0.2, align=1, color=(1.0, 0.3, 0.9, 1.0))
        self.font.end_drawing(ortho2d)

        

    def draw_scene(self, shader: Shader, view: Matrix4, proj: Matrix4, cull_level: bool=True):
        if cull_level: glDisable(GL_CULL_FACE)
        self.draw_level(shader, view, proj)
        if cull_level: glEnable(GL_CULL_FACE)

        self.draw_snake(shader, view, proj)
        self.draw_apples(shader, view, proj)

        score_pos = Matrix4.from_translation(Vector3(0.0, 0.0, -15.0))
        score_rot = Matrix4.from_angle_axis(-math.pi/4, Vector3(1, 0, 0))
        score_scl = Matrix4.from_scale(Vector3(2.2, 2.2, 2.2))
        self.font.begin_drawing()
        self.font.draw_3d(f'Score: {self.score:06d}', transform=score_pos * score_rot * score_scl, align=1)
        self.font.end_drawing(proj * view)

    def draw_shadows(self):
        self.shadow_shader.use()
        self.shadow_buffer.bind()
        glClear(GL_DEPTH_BUFFER_BIT)
        self.draw_scene(self.shadow_shader, self.light.to_matrix4().inverse(), lightProj, False)
        self.shadow_buffer.unbind()

    def draw_level(self, shader: Shader, view: Matrix4, proj: Matrix4):
        shader.use()
        shader.set_uniform('uView', *view.raw)
        shader.set_uniform('uProj', *proj.raw)
        shader.set_uniform('tex', 0)

        self.level_tex.bind(0)
        self.sample.bind(0)

        for mesh in self.level_meshes.values():
            shader.set_uniform('uModel', *self.ground.to_matrix4().raw)
            mesh.draw()

    def draw_apples(self, shader: Shader, view: Matrix4, proj: Matrix4):
        shader.use()
        shader.set_uniform('uView', *view.raw)
        shader.set_uniform('uProj', *proj.raw)
        shader.set_uniform('tex', 0)

        self.apple_tex.bind(0)
        self.sample.bind(0)

        for apple in self.apples:
            apple.draw(shader)

    def draw_snake(self, shader: Shader, view: Matrix4, proj: Matrix4):
        shader.use()
        shader.set_uniform('uView', *view.raw)
        shader.set_uniform('uProj', *proj.raw)
        shader.set_uniform('tex', 0)

        self.snake_tex.bind(0)
        self.sample.bind(0)

        i = 0
        for xform in self.snake_body:
            model = xform.to_matrix4()
            shader.set_uniform('uModel', *model.raw)

            if i == 0:
                self.snake_head_mesh.draw()
            elif i == len(self.snake_body)-1:
                self.snake_tail_mesh.draw()
            else:
                self.snake_body_mesh.draw()

            i += 1


if __name__ == '__main__':
    App().run()
