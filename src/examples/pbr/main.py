import pyge_import

from pyge.application import Application
from pyge.rendering import Mesh, Shader, TextureCubeMap, PrefilteredCubeMap, Texture2D, Utils, Model
from pyge.vmath import Matrix4, Vector3, Vector2, Transform, Quaternion

from deferred_renderer import PBRMaterial, DeferredRenderer, GBufferPass

import math, pygame, random
import numpy as np
from OpenGL.GL import *

assets = pyge_import.assets_folder

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        self.sphere_count = 1

        self.renderer = DeferredRenderer(self.display.get_width(), self.display.get_height())

        # Camera-related
        cam_pos = Vector3(-2.0, 3.0, (24.0 * self.sphere_count / 5))
        self.camera = Transform(translation=cam_pos, rotation=Quaternion.from_look_at(cam_pos, Vector3(0.0, 0.0, 0.0)))
        self.projection = Matrix4.from_perspective(math.pi / 5, self.aspect, 0.01, 500.0)

        # Application-related        
        self.test_mesh = Mesh.from_wavefront(f'{assets}/test.obj')['mesh']
        self.albedo_tex = Texture2D.from_image_file(f'{assets}/albedo.png')
        self.rm_tex = Texture2D.from_image_file(f'{assets}/roughness_metallic.png')

        self.rotation = 0.0

        self.materials = []
        for _ in range(self.sphere_count ** 2):
            r = random.uniform(0.01, 0.8)
            g = random.uniform(0.01, 0.8)
            b = random.uniform(0.01, 0.8)
            rough = random.uniform(0.0, 1.0)
            metal = random.uniform(0.0, 1.0)
            mat = PBRMaterial()
            mat.roughness = rough
            mat.metallic = metal
            mat.base_color = Vector3(r, g, b)
            mat.albedo = self.albedo_tex
            mat.roughness_metallic_map = self.rm_tex
            self.materials.append(mat)

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
        self.renderer.view_matrix = self.camera.to_matrix4()
        self.renderer.projection_matrix = self.projection
        
        lighting_pass = self.renderer.get_pass('lighting')
        lighting_pass.env_map = self.env_map

        count = self.sphere_count
        div_count = (count-1) if count > 1 else 1
        for y in range(count):
            for x in range(count):
                if count == 1:
                    fx = 0.0
                    fy = 0.0
                else:
                    fx = ((x / div_count) * 2.0 - 1.0) * (div_count+0.2)
                    fy = ((y / div_count) * 2.0 - 1.0) * (div_count+0.2)

                xform = Transform(translation=Vector3(fx, fy, 0.0), rotation=Quaternion.from_angle_axis(self.rotation, Vector3(0,1,0)))
                
                self.renderer.submit(Model(
                    self.test_mesh, xform,
                    self.materials[x + y * count]
                ))

        glClearColor(0.0, 0.0, 0.0, 0.0)
        self.renderer.render()

        gbuffer_pass: GBufferPass = self.renderer.get_pass('gbuffer')

        q = 1.0 / 4.0
        y = 0.0
        for i in range(4):
            Utils.draw_quad(gbuffer_pass.gbuffer.color_attachments[i], i*q, 0.0, q, q)
        y += q

        Utils.draw_quad(gbuffer_pass.gbuffer.depth_attachment, 0.0, y, q, q)

if __name__ == '__main__':
    App().run()
