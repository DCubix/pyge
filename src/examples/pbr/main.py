import pyge_import

from pyge.application import Application
from pyge.rendering import Mesh, Shader, Texture2D, TextureCubeMap, Sampler, RenderTarget, Utils, Font, PrefilteredCubeMap
from pyge.vmath import Matrix4, Vector3, Transform, Quaternion

import math, pygame, random
import numpy as np
from OpenGL.GL import *

assets = pyge_import.assets_folder

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        # Camera-related
        cam_pos = Vector3(0.0, 3.0, 5.0)
        self.camera = Transform(translation=cam_pos, rotation=Quaternion.from_look_at(cam_pos, Vector3(0.0, 0.0, 0.0)))
        self.projection = Matrix4.from_perspective(math.pi / 5, self.aspect, 0.01, 500.0)

        # Application-related
        self.rotation = 0.0

        self.test_mesh = Mesh.from_wavefront(f'{assets}/test.obj')['mesh']

        self.shader = Shader()
        self.shader.add_shader_from_file(f'{assets}/shaders/default.vert', GL_VERTEX_SHADER)
        self.shader.add_shader_from_file(f'{assets}/shaders/default.frag', GL_FRAGMENT_SHADER)
        self.shader.link()

        self.env_map = TextureCubeMap.from_file(f'{assets}/cubemap1.jpg')

        prefilterer = PrefilteredCubeMap(self.env_map)
        self.env_map = prefilterer.process()
    
    def on_update(self, deltaTime: float):
        self.rotation += deltaTime

    def on_draw(self):
        glClearColor(0.0, 0.1, 0.35, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.shader.use()

        self.env_map.bind(0)
        self.shader.set_uniform('uEnvMap', 0)

        model = Matrix4.from_translation(Vector3(0.0, -1.0, 0.0)) * Matrix4.from_angle_axis(self.rotation, Vector3(0.0, 1.0, 0.0))

        self.shader.set_uniform_vector('uProjection', self.projection)
        self.shader.set_uniform_vector('uView', self.camera.to_matrix4().inverse())
        self.shader.set_uniform_vector('uModel', model)

        self.shader.set_uniform_vector('uEyePosition', self.camera.translation)
        self.shader.set_uniform('uTime', self.rotation)

        self.test_mesh.draw()


if __name__ == '__main__':
    App().run()
