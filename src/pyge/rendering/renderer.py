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

class Pass:
    def __init__(self, repeat_count: int = 1):
        self._repeat_count = max(1, repeat_count)

    @property
    def repeat_count(self):
        return self._repeat_count

    # TODO: on_render_instanced?
    def on_render(self, models: List[Model], proj: Matrix4, view: Matrix4):
        pass

class Renderer:
    def __init__(self, view_width: int, view_height: int):
        self._passes: Dict[str, Pass] = {}
        self._models: List[Model] = []

        self.view_matrix = Matrix4()
        self.projection_matrix = Matrix4()

        self.view_width = view_width
        self.view_height = view_height

    def add_pass(self, name: str, pass_object: Pass):
        self._passes[name] = pass_object

    def get_pass(self, name: str):
        return self._passes[name]

    def submit(self, model: Model):
        self._models.append(model)

    def render(self):
        for _, p in self._passes.items():
            p.on_render(self._models, self.projection_matrix, self.view_matrix)
        self._models = []
