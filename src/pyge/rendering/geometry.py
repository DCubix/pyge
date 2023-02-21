from typing import Tuple, List

import ctypes, re, itertools
import numpy as np
import numpy.typing as npt

from OpenGL.GL import *

class VertexFormat:
	def __init__(self):
		self.fields = []

	@property
	def size(self):
		sum = 0
		for size, _, _ in self.fields:
			sum += size
		return sum

	@property
	def stride(self):
		sum = 0
		for size, _, type in self.fields:
			sum += size * self._sizeofGLtype(type)
		return sum
	
	@staticmethod
	def _sizeofGLtype(type: GLenum):
		if type == GL_BYTE or type == GL_UNSIGNED_BYTE:
			return ctypes.sizeof(GLbyte)
		elif type == GL_SHORT or type == GL_UNSIGNED_SHORT:
			return ctypes.sizeof(GLshort)
		elif type in [GL_INT, GL_UNSIGNED_INT]:
			return ctypes.sizeof(GLint)
		elif type == GL_FLOAT:
			return ctypes.sizeof(GLfloat)
		elif type == GL_DOUBLE:
			return ctypes.sizeof(GLdouble)
		elif type == GL_HALF_FLOAT:
			return ctypes.sizeof(GLhalfARB)
		elif type == GL_FIXED:
			return ctypes.sizeof(GLfixed)
		else:
			return 0

	def add_field(self, size: int, normalized: bool=False, type: GLenum=GL_FLOAT):
		self.fields.append((size, normalized, type))

	def apply(self):
		stride = self.stride
		offset = 0
		index = 0
		for size, normalized, type in self.fields:
			glEnableVertexAttribArray(index)
			glVertexAttribPointer(
				index,
				size,
				type,
				GL_TRUE if normalized else GL_FALSE,
				stride,
				ctypes.c_void_p(offset)
			)
			offset += size * self._sizeofGLtype(type)
			index += 1
	
	@staticmethod
	def from_list(fmt: List[Tuple[int, bool, GLenum]]):
		vformat = VertexFormat()
		for size, norm, type in fmt:
			vformat.add_field(size, norm, type)
		return vformat


class Buffer:
	def __init__(self, target: GLenum, usage: GLenum):
		self.target = target
		self.usage = usage
		self.id = glGenBuffers(1)
		self.data_length = 0

	def update(self, data: npt.NDArray, offset: int=0):
		self.bind()
		if self.data_length < data.size:
			glBufferData(self.target, data.size * data.itemsize, data, self.usage)
			self.data_length = data.size
		else:
			glBufferSubData(self.target, offset, data.size * data.itemsize, data)

	def bind(self):
		glBindBuffer(self.target, self.id)


class Mesh:
	def __init__(self, format: VertexFormat):
		self.format = format

		self.vbo = Buffer(GL_ARRAY_BUFFER, GL_DYNAMIC_DRAW)
		self.ibo = Buffer(GL_ELEMENT_ARRAY_BUFFER, GL_DYNAMIC_DRAW)
		self.vao = glGenVertexArrays(1)

		glBindVertexArray(self.vao)
		self.vbo.bind()

		self.format.apply()

		self.ibo.bind()

		glBindVertexArray(0)
	
	def update(self, vertices: npt.NDArray[np.float32], indices: npt.NDArray[np.uint32]):
		self.vbo.update(vertices)
		self.ibo.update(indices)

	def draw(self, primitive: GLenum=GL_TRIANGLES, count: int=-1, offset: int=0):
		count = self.ibo.data_length if count <= 0 else count
		glBindVertexArray(self.vao)
		glDrawElements(primitive, count, GL_UNSIGNED_INT, ctypes.c_void_p(offset * ctypes.sizeof(ctypes.c_uint)))

	@staticmethod
	def from_wavefront(file_path: str):
		fmt = VertexFormat.from_list([
			(3, False, GL_FLOAT),
			(3, True, GL_FLOAT),
			(2, False, GL_FLOAT)
		])

		lines = []
		with open(file_path, 'r') as fp:
			lines = fp.readlines()
		
		raw_positions = []
		raw_normals = []
		raw_tex_coords = []
		raw_faces = [] # [(vi, ti, ni), ...]

		for line in lines:
			line = line.strip()
			tok = re.split(r'\s', line)

			if tok[0] == 'v':
				values = [float(v) for v in tok[1:]]
				raw_positions.append(tuple(values))
			elif tok[0] == 'vt':
				values = [float(v) for v in tok[1:]]
				raw_tex_coords.append(tuple(values))
			elif tok[0] == 'vn':
				values = [float(v) for v in tok[1:]]
				raw_normals.append(tuple(values))
			elif tok[0] == 'f':
				face_defs = tok[1:]
				
				for fdef in face_defs:
					fields = [int(v) if len(v) > 0 else None for v in fdef.split('/')]
					
					if len(fields) == 1: # pos pos pos ...
						raw_faces.append((fields[0]-1, None, None))
					elif len(fields) == 2: # pos/tex pos/tex pos/tex ...
						raw_faces.append((fields[0]-1, fields[1]-1, None))
					elif len(fields) == 3:
						if fields[1] is None: # pos//norm pos//norm pos//norm ...
							raw_faces.append((fields[0]-1, None, fields[2]-1))
						else: # pos/tex/norm pos/tex/norm pos/tex/norm ...
							raw_faces.append((fields[0]-1, fields[1]-1, fields[2]-1))
			else:
				continue

		vertices = []
		indices = []

		i = 0
		for v, vt, vn in raw_faces:
			vertices.extend(list(raw_positions[v]))

			if vn:
				vertices.extend(list(raw_normals[vn]))
			else:
				vertices.extend([0.0, 0.0, 0.0])
			
			if vt:
				vertices.extend(list(raw_tex_coords[vt]))
			else:
				vertices.extend([0.0, 0.0])

			indices.append(i)
			i += 1

		mesh = Mesh(fmt)
		mesh.update(np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32))

		return mesh
