from typing import Tuple

import OpenGL.GL
from OpenGL.GL import *
from OpenGL.GL.shaders import compileShader, compileProgram

class Shader:
	def __init__(self):
		self.program = None

		self._shaders = []
		self._uniforms = {}
		self._attributes = {}
	
	def add_shader(self, source: str, type: GLenum):
		self._shaders.append(compileShader(source, type))

	def add_shader_from_file(self, file_path: str, type: GLenum):
		source = ""
		with open(file_path) as fp:
			source = fp.read()
		self.add_shader(source, type)
	
	def link(self):
		self.program = compileProgram(*self._shaders)
	
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
