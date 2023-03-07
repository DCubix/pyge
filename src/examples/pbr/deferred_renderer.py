import pyge_import
assets = pyge_import.assets_folder

from typing import List

from pyge.rendering import Pass, Renderer, Model, RenderTarget, Shader, ShaderCache, Material, Texture2D, Utils, Sampler, TextureCubeMap, ImageBasedLightingBRDFLUT
from pyge.vmath import Matrix4, Vector3

from OpenGL.GL import *

class PBRMaterial(Material):
    def __init__(self):
        self.albedo: Texture2D = None
        self.normal_map: Texture2D = None
        self.roughness_metallic_map: Texture2D = None

        self.base_color: Vector3 = Vector3(1.0, 1.0, 1.0)
        self.roughness = 0.5
        self.metallic = 0.0

    def on_apply(self, shader: Shader):
        shader.set_uniform('uRoughnessMetallic', self.roughness, self.metallic)
        shader.set_uniform_vector('uBaseColor', self.base_color)

class GBufferPass(Pass):
    def __init__(self, view_width: int, view_height: int):
        super().__init__(1)

        self.gbuffer = RenderTarget(view_width, view_height)
        self.gbuffer.add_color_attachment(GL_RGB8) ## Color/Albedo
        self.gbuffer.add_color_attachment(GL_RGB8) ## Normals
        self.gbuffer.add_color_attachment(GL_RGB32F) ## Positions
        self.gbuffer.add_color_attachment(GL_RGB8) ## Material (Rough, Metallic...)
        self.gbuffer.add_depth_attachment()

        self.shader = ShaderCache.get('_gbuffer')
        if not self.shader.linked:
            self.shader.add_shader_from_file(f'{assets}/shaders/gbuffer.vert', GL_VERTEX_SHADER)
            self.shader.add_shader_from_file(f'{assets}/shaders/gbuffer.frag', GL_FRAGMENT_SHADER)
            self.shader.link()

    def on_render(self, models: List[Model], proj: Matrix4, view: Matrix4):
        Utils.push_enable_state([ GL_DEPTH_TEST, GL_CULL_FACE ])

        self.gbuffer.bind()
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.shader.use()

        self.shader.set_uniform_vector('uProjection', proj)
        self.shader.set_uniform_vector('uView', view.inverse())

        for model in models:
            self.shader.set_uniform_vector('uModel', model.transform.to_matrix4())
            model.material.on_apply(self.shader)

            mat: PBRMaterial = model.material
            self.shader.set_uniform('uAlbedoMapOn', 1 if mat.albedo else 0)
            self.shader.set_uniform('uRoughnessMetallicMapOn', 1 if mat.roughness_metallic_map else 0)

            slot = 0
            if mat.albedo:
                mat.albedo.bind(slot)
                self.shader.set_uniform('uAlbedoMap', slot)
                slot += 1
            
            if mat.albedo:
                mat.roughness_metallic_map.bind(slot)
                self.shader.set_uniform('uRoughnessMetallicMap', slot)
                slot += 1

            model.mesh.draw(model.mesh_primitive, model.mesh_vertex_count, model.mesh_vertex_offset)

        self.gbuffer.unbind()

        Utils.pop_enable_state()


class LightingPass(Pass):
    def __init__(self, gbuffer: RenderTarget):
        super().__init__(1)

        self.shader = ShaderCache.get('_lighting')
        if not self.shader.linked:
            self.shader.add_shader_from_file(f'{assets}/shaders/lighting.vert', GL_VERTEX_SHADER)
            self.shader.add_shader_from_file(f'{assets}/shaders/lighting.frag', GL_FRAGMENT_SHADER)
            self.shader.link()

        self.gbuffer = gbuffer
        self.env_map: TextureCubeMap = None

        envBRDF_gen = ImageBasedLightingBRDFLUT(512, 512)
        self.env_brdf = envBRDF_gen.process()

        self.linear_sampler = Sampler()
        self.linear_sampler.filter()
        self.linear_sampler.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)

        self.mip_sampler = Sampler()
        self.mip_sampler.filter()
        self.mip_sampler.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)

        self.near_sampler = Sampler()
        self.near_sampler.filter(GL_NEAREST, GL_NEAREST)
        self.near_sampler.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)

    def on_render(self, models: List[Model], proj: Matrix4, view: Matrix4):
        self.shader.use()

        self.gbuffer.color_attachments[0].bind(0)
        self.gbuffer.color_attachments[1].bind(1)
        self.gbuffer.color_attachments[2].bind(2)
        self.gbuffer.color_attachments[3].bind(3)

        self.env_map.bind(4)
        self.env_brdf.bind(5)

        self.near_sampler.bind(1)
        self.near_sampler.bind(2)
        self.near_sampler.bind(5)

        self.near_sampler.bind(0)
        self.near_sampler.bind(3)

        self.linear_sampler.bind(4)

        self.shader.set_uniform('uGB_Albedo', 0)
        self.shader.set_uniform('uGB_Normals', 1)
        self.shader.set_uniform('uGB_Positions', 2)
        self.shader.set_uniform('uGB_Material', 3)

        self.shader.set_uniform('uEnvMap', 4)
        self.shader.set_uniform('uEnvBRDF', 5)

        self.shader.set_uniform_vector('uEyePosition', view.to_transform().translation)

        glClear(GL_COLOR_BUFFER_BIT)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, ctypes.c_void_p(0))


class DeferredRenderer(Renderer):
    def __init__(self, view_width: int, view_height: int):
        super().__init__(view_width, view_height)

        self.add_pass('gbuffer', GBufferPass(view_width, view_height))
        self.add_pass('lighting', LightingPass(self.get_pass('gbuffer').gbuffer))
