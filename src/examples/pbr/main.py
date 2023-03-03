import pyge_import

from pyge.application import Application
from pyge.rendering import Mesh, Shader, TextureCubeMap, Sampler, PrefilteredCubeMap, ImageBasedLightingBRDFLUT
from pyge.vmath import Matrix4, Vector3, Transform, Quaternion

import math, pygame, random
import numpy as np
from OpenGL.GL import *

assets = pyge_import.assets_folder

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        # Camera-related
        cam_pos = Vector3(12.0, 5.0, 30.0)
        self.camera = Transform(translation=cam_pos, rotation=Quaternion.from_look_at(cam_pos, Vector3(0.0, 0.0, 0.0)))
        self.projection = Matrix4.from_perspective(math.pi / 5, self.aspect, 0.01, 500.0)

        # Application-related
        self.rotation = 0.0

        self.test_mesh = Mesh.from_wavefront(f'{assets}/ball.obj')['mesh']

        self.shader = Shader()
        self.shader.add_shader_from_file(f'{assets}/shaders/default.vert', GL_VERTEX_SHADER)
        self.shader.add_shader_from_file(f'{assets}/shaders/default.frag', GL_FRAGMENT_SHADER)
        self.shader.link()

        self.env_map = TextureCubeMap.from_file(f'{assets}/cubemap2.jpg')

        prefilterer = PrefilteredCubeMap(self.env_map)
        self.env_map = prefilterer.process()

        envBRDF_gen = ImageBasedLightingBRDFLUT(512, 512)
        self.env_brdf = envBRDF_gen.process()

        self.env_sampler = Sampler()
        self.env_sampler.filter()
        self.env_sampler.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)

        self.default_sampler = Sampler()
        self.default_sampler.filter()
        self.default_sampler.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)
    
    def on_update(self, deltaTime: float):
        self.rotation += deltaTime

    def on_draw(self):
        glClearColor(0.0, 0.1, 0.35, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.shader.use()

        self.env_map.bind(0)
        self.shader.set_uniform('uEnvMap', 0)

        self.env_brdf.bind(1)
        self.shader.set_uniform('uEnvBRDF', 1)
        
        self.env_sampler.bind(0)
        self.default_sampler.bind(1)

        self.shader.set_uniform_vector('uProjection', self.projection)
        self.shader.set_uniform_vector('uView', self.camera.to_matrix4().inverse())
        self.shader.set_uniform_vector('uEyePosition', self.camera.translation)
        self.shader.set_uniform('uTime', self.rotation)

        for y in range(7):
            for x in range(7):
                fx = ((x / 6) * 2.0 - 1.0) * 6.5
                fy = ((y / 6) * 2.0 - 1.0) * 6.5

                model = Matrix4.from_translation(Vector3(fx, fy, 0.0)) # * Matrix4.from_angle_axis(self.rotation, Vector3(0.0, 1.0, 0.0))

                self.shader.set_uniform('uRoughnessMetallic', x/6, y/6)
                self.shader.set_uniform_vector('uModel', model)

                self.test_mesh.draw()


if __name__ == '__main__':
    App().run()
