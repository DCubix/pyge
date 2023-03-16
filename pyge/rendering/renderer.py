from typing import List

from .geometry import Mesh
from ..vmath import Matrix4, Transform, Vector4, Vector3
from ..rendering import Shader

from OpenGL.GL import GLenum, GL_TRIANGLES

import math

class Material:
    def on_apply(self, shader: Shader):
        pass

class Model:
    def __init__(
        self,
        mesh: Mesh,
        xform: Matrix4,
        material: Material = Material(),
        primitive: GLenum=GL_TRIANGLES,
        count: int=-1,
        offset: int=0
    ):
        self.mesh = mesh
        self.transform = xform
        self.mesh_primitive = primitive
        self.mesh_vertex_count = count
        self.mesh_vertex_offset = offset
        self.material = material

# Light Types
class Light:
    def __init__(self):
        self.color = Vector4(1.0, 1.0, 1.0, 1.0)
    
    def apply(self, shader: Shader, uniform: str):
        shader.set_uniform_vector(f'{uniform}.color', self.color)

class DirectionalLight(Light):
    def __init__(self):
        super().__init__()
        self.direction = Vector3(1.0, 1.0, 0.0)
    
    def apply(self, shader: Shader, uniform: str):
        super().apply(shader, uniform)
        shader.set_uniform(f'{uniform}.type', 0)
        shader.set_uniform_vector(f'{uniform}.direction', self.direction)

class PointLight(Light):
    def __init__(self):
        super().__init__()
        self.position = Vector3()
        self.radius = 1.0
    
    def apply(self, shader: Shader, uniform: str):
        super().apply(shader, uniform)
        shader.set_uniform(f'{uniform}.type', 1)
        shader.set_uniform(f'{uniform}.radius', self.radius)
        shader.set_uniform_vector(f'{uniform}.position', self.position)

class SpotLight(PointLight):
    def __init__(self):
        super().__init__()
        self.direction = Vector3(1.0, 1.0, 0.0)
        self.cutoff = math.pi / 3.5

    def apply(self, shader: Shader, uniform: str):
        super().apply(shader, uniform)
        shader.set_uniform(f'{uniform}.type', 2)
        shader.set_uniform(f'{uniform}.cutoff', self.cutoff)
        shader.set_uniform_vector(f'{uniform}.direction', self.direction)

class Renderer:
    def __init__(self, view_width: int, view_height: int):
        self._models: List[Model] = []
        self._lights: List[Light] = []

        self.view_matrix = Matrix4()
        self.projection_matrix = Matrix4()

        self.view_width = view_width
        self.view_height = view_height

    def submit(self, model: Model):
        self._models.append(model)

    def submit_light(self, light: Light):
        self._lights.append(light)

    def flush(self):
        self._models = []
        self._lights = []

    def render(self):
        pass
