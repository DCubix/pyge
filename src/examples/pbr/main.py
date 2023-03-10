import pyge_import

from pyge.application import Application
from pyge.rendering import Mesh, Shader, TextureCubeMap, PrefilteredCubeMap, Texture2D, Utils, Model, PointLight
from pyge.vmath import Matrix4, Vector3, Vector2, Transform, Quaternion, Vector4

from deferred_renderer import PBRMaterial, DeferredRenderer

import math, random, colorsys
import numpy as np
from OpenGL.GL import *

assets = pyge_import.assets_folder

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        self.sphere_count = 3

        self.renderer = DeferredRenderer(self.display.get_width(), self.display.get_height())

        # Camera-related
        cam_pos = Vector3(-8.0, 2.0, (15.0 * self.sphere_count / 5))
        self.camera = Transform(translation=cam_pos, rotation=Quaternion.from_look_at(cam_pos, Vector3(0.0, 0.0, 0.0)))
        self.projection = Matrix4.from_perspective(math.pi / 5, self.aspect, 0.01, 500.0)

        # Application-related        
        self.test_mesh = Mesh.from_wavefront(f'{assets}/ball.obj')['mesh']
        self.albedo_tex = Texture2D.from_image_file(f'{assets}/rust_albedo.png')
        self.rm_tex = Texture2D.from_image_file(f'{assets}/rust_roughness_metallic.png')

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
            #mat.albedo_map = self.albedo_tex
            #mat.roughness_metallic_map = self.rm_tex
            #mat.albedo_map_triplanar = True
            #mat.roughness_metallic_triplanar = True
            self.materials.append(mat)

        self.shader = Shader()
        self.shader.add_shader_from_file(f'{assets}/shaders/default.vert', GL_VERTEX_SHADER)
        self.shader.add_shader_from_file(f'{assets}/shaders/default.frag', GL_FRAGMENT_SHADER)
        self.shader.link()

        env_map = TextureCubeMap.from_file(f'{assets}/cubemap2.jpg')
        self.renderer.env_map = PrefilteredCubeMap(env_map).process()

        self.light_positions: list[Vector3] = []
        self.light_colors: list[Vector3] = []

        for _ in range(20):
            r, g, b = colorsys.hsv_to_rgb(random.uniform(0.0, 1.0), 0.8, 1.0)
            self.light_colors.append(Vector4(r, g, b, random.uniform(1.0, 4.0)))
            self.light_positions.append(Vector3(
                random.uniform(-6.0, 6.0),
                random.uniform(-10.0, 10.0),
                random.uniform(-6.0, 6.0)
            ))
    
    def on_update(self, deltaTime: float):
        self.rotation += deltaTime

        for lp in self.light_positions:
            lp.y += deltaTime * 1.5
            if lp.y >= 10.0:
                lp.y = -10.0

        dist = (30.0 * self.sphere_count / 5)
        self.camera.translation.x = math.cos(self.rotation * 0.5) * dist
        self.camera.translation.z = math.sin(self.rotation * 0.5) * dist
        self.camera.translation.y = 7.0
        self.camera.rotation = Quaternion.from_look_at(self.camera.translation, Vector3(0.0, 0.0, 0.0))

    def on_draw(self):
        self.renderer.view_matrix = self.camera.to_matrix4()
        self.renderer.projection_matrix = self.projection

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

                xform = Transform(translation=Vector3(fx, fy, 0.0))
                
                self.renderer.submit(Model(
                    self.test_mesh, xform,
                    self.materials[x + y * count]
                ))

        # add lights
        for i in range(len(self.light_positions)):
            p = PointLight()
            p.position = self.light_positions[i]
            p.color = self.light_colors[i]
            p.radius = 3.5
            self.renderer.submit_light(p)

        glClearColor(0.0, 0.0, 0.0, 0.0)
        self.renderer.render()

        # gbuffer = self.renderer.gbuffer

        # q = 1.0 / 4.0
        # y = 0.0
        # for i in range(4):
        #     Utils.draw_quad(gbuffer.color_attachments[i], i*q, 0.0, q, q)
        # y += q

        # Utils.draw_quad(gbuffer.depth_attachment, 0.0, y, q, q)

if __name__ == '__main__':
    App().run()
