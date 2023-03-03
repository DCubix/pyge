from typing import Dict

import OpenGL.GL
from OpenGL.GL import *
from OpenGL.GL.shaders import compileShader, compileProgram

from pyge.vmath import Vector2, Vector3, Vector4, Matrix4

class Shader:
	def __init__(self):
		self.program = None

		self._shaders = []
		self._uniforms = {}
		self._attributes = {}
		self._linked = False
	
	@property
	def linked(self):
		return self._linked

	def add_shader(self, source: str, type: GLenum):
		self._shaders.append(compileShader(source, type))

	def add_shader_from_file(self, file_path: str, type: GLenum):
		source = ""
		with open(file_path) as fp:
			source = fp.read()
		self.add_shader(source, type)
	
	def link(self):
		self.program = compileProgram(*self._shaders)
		self._linked = True
	
	def discard(self):
		glDeleteProgram(self.program)

	def use(self):
		glUseProgram(self.program)
	
	def get_uniform_location(self, name: str):
		loc = glGetUniformLocation(self.program, name)
		if loc != -1:
			self._uniforms[name] = loc
		else:
			return None
		return self._uniforms[name]

	def set_uniform_vector(self, name: str, v: Vector2 | Vector3 | Vector4 | Matrix4):
		loc = self.get_uniform_location(name)
		if loc is None: return

		if isinstance(v, Vector2):
			glUniform2f(loc, v.x, v.y)
		elif isinstance(v, Vector3):
			glUniform3f(loc, v.x, v.y, v.z)
		elif isinstance(v, Vector4):
			glUniform4f(loc, v.x, v.y, v.z, v.w)
		elif isinstance(v, Matrix4):
			glUniformMatrix4fv(loc, 1, False, v.raw)
		else:
			return

	def set_uniform(self, name: str, *value):
		if len(value) == 0: raise Exception(f'Invalid value.')
		if not isinstance(value[0], float) and not isinstance(value[0], int): raise Exception(f'Invalid value type: "{type(value[0])}"')

		loc = self.get_uniform_location(name)
		if loc is None: return
		
		tp = 'f'
		if isinstance(value[0], int):
			tp = 'i'

		match len(value):
			case n if n in range(1, 5): getattr(OpenGL.GL, f'glUniform{n}{tp}')(loc, *value)
			case 9: glUniformMatrix3fv(loc, 1, False, list(value))
			case 16: glUniformMatrix4fv(loc, 1, False, list(value))
			case _: raise f'Invalid value.'

class ShaderCache:
	cache: Dict[str, Shader] = {}

	@staticmethod
	def get(name: str) -> Shader:
		if name not in ShaderCache.cache:
			ShaderCache.cache[name] = Shader()
		return ShaderCache.cache[name]
