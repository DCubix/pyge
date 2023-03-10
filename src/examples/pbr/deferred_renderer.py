import pyge_import
assets = pyge_import.assets_folder

from typing import List

from pyge.rendering import Renderer, Model, RenderTarget, Shader, ShaderCache, Material, Texture2D, Utils, Sampler, TextureCubeMap, ImageBasedLightingBRDFLUT
from pyge.vmath import Matrix4, Vector3

from OpenGL.GL import *

class PBRMaterial(Material):
    def __init__(self):
        self.albedo_map: Texture2D = None
        self.normal_map: Texture2D = None
        self.roughness_metallic_map: Texture2D = None

        self.albedo_map_triplanar = False
        self.normal_map_triplanar = False
        self.roughness_metallic_triplanar = False

        self.base_color: Vector3 = Vector3(1.0, 1.0, 1.0)
        self.roughness = 0.5
        self.metallic = 0.0

    def on_apply(self, shader: Shader):
        shader.set_uniform('uRoughnessMetallic', self.roughness, self.metallic)
        shader.set_uniform_vector('uBaseColor', self.base_color)

class DeferredRenderer(Renderer):
    def __init__(self, view_width: int, view_height: int):
        super().__init__(view_width, view_height)

        # GBuffer Pass
        self.gbuffer = RenderTarget(view_width, view_height)
        self.gbuffer.add_color_attachment(GL_RGB8) ## Color/Albedo
        self.gbuffer.add_color_attachment(GL_RGB8) ## Normals
        self.gbuffer.add_color_attachment(GL_RGB32F) ## Positions
        self.gbuffer.add_color_attachment(GL_RGB8) ## Material (Rough, Metallic...)
        self.gbuffer.add_depth_attachment()

        self.gbuffer_shader = ShaderCache.get('_gbuffer')
        if not self.gbuffer_shader.linked:
            self.gbuffer_shader.add_shader_from_file(f'{assets}/shaders/gbuffer.vert', GL_VERTEX_SHADER)
            self.gbuffer_shader.add_shader_from_file(f'{assets}/shaders/gbuffer.frag', GL_FRAGMENT_SHADER)
            self.gbuffer_shader.link()

        self.sampler = Sampler()
        self.sampler.filter()
        self.sampler.wrap(GL_REPEAT, GL_REPEAT)

        # Lighting Pass
        self.lighting_shader = ShaderCache.get('_lighting')
        if not self.lighting_shader.linked:
            self.lighting_shader.add_shader_from_file(f'{assets}/shaders/lighting.vert', GL_VERTEX_SHADER)
            self.lighting_shader.add_shader_from_file(f'{assets}/shaders/lighting.frag', GL_FRAGMENT_SHADER)
            self.lighting_shader.link()

        self.env_map: TextureCubeMap = None
        self.env_brdf = ImageBasedLightingBRDFLUT(512, 512).process()

        self.linear_sampler = Sampler()
        self.linear_sampler.filter()
        self.linear_sampler.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)

        self.mip_sampler = Sampler()
        self.mip_sampler.filter()
        self.mip_sampler.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)

        self.near_sampler = Sampler()
        self.near_sampler.filter(GL_NEAREST, GL_NEAREST)
        self.near_sampler.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)

    def _pass_gbuffer(self):
        Utils.push_enable_state([ GL_DEPTH_TEST, GL_CULL_FACE ])

        self.gbuffer.bind()
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.gbuffer_shader.use()

        self.gbuffer_shader.set_uniform_vector('uProjection', self.projection_matrix)
        self.gbuffer_shader.set_uniform_vector('uView', self.view_matrix.inverse())

        for model in self._models:
            self.gbuffer_shader.set_uniform_vector('uModel', model.transform.to_matrix4())
            model.material.on_apply(self.gbuffer_shader)

            mat: PBRMaterial = model.material

            self.gbuffer_shader.set_uniform('uAlbedoMapTriplanar', 1 if mat.albedo_map_triplanar else 0)
            self.gbuffer_shader.set_uniform('uRoughnessMetallicMapTriplanar', 1 if mat.roughness_metallic_triplanar else 0)

            self.gbuffer_shader.set_uniform('uAlbedoMapOn', 1 if mat.albedo_map else 0)
            self.gbuffer_shader.set_uniform('uRoughnessMetallicMapOn', 1 if mat.roughness_metallic_map else 0)

            slot = 0
            if mat.albedo_map:
                self.sampler.bind(slot)
                mat.albedo_map.bind(slot)
                self.gbuffer_shader.set_uniform('uAlbedoMap', slot)
                slot += 1
            
            if mat.roughness_metallic_map:
                self.sampler.bind(slot)
                mat.roughness_metallic_map.bind(slot)
                self.gbuffer_shader.set_uniform('uRoughnessMetallicMap', slot)
                slot += 1

            model.mesh.draw(model.mesh_primitive, model.mesh_vertex_count, model.mesh_vertex_offset)

        self.gbuffer.unbind()

        Utils.pop_enable_state()

    def _pass_lighting(self):
        Utils.push_enable_state([ GL_BLEND ])

        glBindVertexArray(Utils.get_dummy_vao())

        self.lighting_shader.use()

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

        self.lighting_shader.set_uniform('uGB_Albedo', 0)
        self.lighting_shader.set_uniform('uGB_Normals', 1)
        self.lighting_shader.set_uniform('uGB_Positions', 2)
        self.lighting_shader.set_uniform('uGB_Material', 3)

        self.lighting_shader.set_uniform('uEnvMap', 4)
        self.lighting_shader.set_uniform('uEnvBRDF', 5)

        self.lighting_shader.set_uniform_vector('uEyePosition', self.view_matrix.to_transform().translation)

        glClear(GL_COLOR_BUFFER_BIT)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # ambient mode
        self.lighting_shader.set_uniform('uLightingMode', 0)
        glDrawArrays(GL_TRIANGLES, 0, 6)

        # lights mode
        self.lighting_shader.set_uniform('uLightingMode', 1)

        glBlendFunc(GL_ONE, GL_ONE)
        for light in self._lights:
            light.apply(self.lighting_shader, 'uLight')
            glDrawArrays(GL_TRIANGLES, 0, 6)
        
        Utils.pop_enable_state()
        glBindVertexArray(0)

        if self.env_map:
            Utils.push_enable_state([ GL_CULL_FACE, GL_DEPTH_TEST ])
            glClear(GL_DEPTH_BUFFER_BIT)

            # blit depth
            self.gbuffer.bind_read()
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0)
            glBlitFramebuffer(
                0, 0, self.view_width, self.view_height,
                0, 0, self.view_width, self.view_height,
                GL_DEPTH_BUFFER_BIT, GL_NEAREST
            )
            self.gbuffer.unbind()

            glCullFace(GL_FRONT)
            Utils.draw_cube(self.env_map, self.projection_matrix, self.view_matrix)
            glCullFace(GL_BACK)
            Utils.pop_enable_state()

    def render(self):
        self._pass_gbuffer()
        self._pass_lighting()
        self.flush()
