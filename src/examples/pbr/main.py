import pyge_import

from pyge.application import Application
from pyge.rendering import Mesh, Shader, TextureCubeMap, Sampler, PrefilteredCubeMap, ImageBasedLightingBRDFLUT
from pyge.vmath import Matrix4, Vector3, Vector2, Transform, Quaternion

import math, pygame, random
import numpy as np
from OpenGL.GL import *

assets = pyge_import.assets_folder

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        self.sphere_count = 4
        self.colors = []
        self.rms = []
        for _ in range(self.sphere_count ** 2):
            r = random.uniform(0.01, 0.8)
            g = random.uniform(0.01, 0.8)
            b = random.uniform(0.01, 0.8)
            self.colors.append(Vector3(r, g, b))

            rough = random.uniform(0.0, 1.0)
            metal = random.uniform(0.0, 1.0)
            self.rms.append(Vector2(rough, metal))

        # Camera-related
        cam_pos = Vector3(0.0, 0.0, (22.0 * self.sphere_count / 5))
        self.camera = Transform(translation=cam_pos, rotation=Quaternion.from_look_at(cam_pos, Vector3(0.0, 0.0, 0.0)))
        self.projection = Matrix4.from_perspective(math.pi / 5, self.aspect, 0.01, 500.0)

        # Application-related
        self.rotation = 0.0

        self.test_mesh = Mesh.from_wavefront(f'{assets}/monke.obj')['mesh']

        self.shader = Shader()
        self.shader.add_shader_from_file(f'{assets}/shaders/default.vert', GL_VERTEX_SHADER)
        self.shader.add_shader_from_file(f'{assets}/shaders/default.frag', GL_FRAGMENT_SHADER)
        self.shader.link()

        self.env_map = TextureCubeMap.from_file(f'{assets}/cubemap1.jpg')

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

        count = self.sphere_count
        div_count = (count-1) if count > 1 else 1
        for y in range(count):
            for x in range(count):
                fx = ((x / div_count) * 2.0 - 1.0) * (div_count+0.2)
                fy = ((y / div_count) * 2.0 - 1.0) * (div_count+0.2)

                model = Matrix4.from_translation(Vector3(fx, fy, 0.0))

                self.shader.set_uniform_vector('uRoughnessMetallic', self.rms[x + y * count])
                self.shader.set_uniform_vector('uModel', model)
                self.shader.set_uniform_vector('uBaseColor', self.colors[x + y * count])

                self.test_mesh.draw()


if __name__ == '__main__':
    App().run()
