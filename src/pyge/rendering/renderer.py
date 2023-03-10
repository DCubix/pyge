from typing import List, Dict

from .geometry import Mesh
from ..vmath import Matrix4, Transform
from ..rendering import Shader

from OpenGL.GL import GLenum, GL_TRIANGLES


class Material:
    def on_apply(self, shader: Shader):
        pass

class Model:
    def __init__(
        self,
        mesh: Mesh,
        xform: Transform,
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

class Renderer:
    def __init__(self, view_width: int, view_height: int):
        self._models: List[Model] = []

        self.view_matrix = Matrix4()
        self.projection_matrix = Matrix4()

        self.view_width = view_width
        self.view_height = view_height

    def submit(self, model: Model):
        self._models.append(model)

    def flush(self):
        self._models = []

    def render(self):
        pass
