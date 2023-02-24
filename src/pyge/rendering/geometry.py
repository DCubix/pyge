from typing import Dict, Tuple, List

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

	def enable(self, vao: GLuint):
		offset = 0
		index = 0
		for size, normalized, type in self.fields:
			glEnableVertexArrayAttrib(vao, index)
			glVertexArrayAttribBinding(vao, index, 0)
			glVertexArrayAttribFormat(vao, index, size, type, GL_TRUE if normalized else GL_FALSE, offset)
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

		self.id = GLuint()
		glCreateBuffers(1, self.id)

		self.data_length = 0

	def update(self, data: npt.NDArray, offset: int=0):
		if self.data_length < data.size:
			glNamedBufferData(self.id, data.size * data.itemsize, data, self.usage)
			self.data_length = data.size
		else:
			glNamedBufferSubData(self.id, offset, data.size * data.itemsize, data)

	def bind(self):
		glBindBuffer(self.target, self.id)


class Mesh:
	def __init__(self, format: VertexFormat):
		self.format = format

		self.vbo = Buffer(GL_ARRAY_BUFFER, GL_DYNAMIC_DRAW)
		self.ebo = Buffer(GL_ELEMENT_ARRAY_BUFFER, GL_DYNAMIC_DRAW)
		self.vao = GLuint()
		glCreateVertexArrays(1, self.vao)

		self.format.enable(self.vao)
		glVertexArrayVertexBuffer(self.vao, 0, self.vbo.id, 0, self.format.stride)
		glVertexArrayElementBuffer(self.vao, self.ebo.id)
	
	def update(self, vertices: npt.NDArray[np.float32], indices: npt.NDArray[np.uint32]):
		self.vbo.update(vertices)
		self.ebo.update(indices)

	def draw(self, primitive: GLenum=GL_TRIANGLES, count: int=-1, offset: int=0):
		count = self.ebo.data_length if count <= 0 else count
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
		
		raw_meshes = []
		raw_positions = {}
		raw_normals = {}
		raw_tex_coords = {}
		raw_faces = {} # [(vi, ti, ni), ...]

		tmp_last_position_id = 0
		tmp_last_normal_id = 0
		tmp_last_tex_coord_id = 0
		last_position_id = 0
		last_normal_id = 0
		last_tex_coord_id = 0

		current_mesh = 'mesh'
		raw_meshes.append(current_mesh)

		for line in lines:
			line = line.strip()
			tok = re.split(r'\s', line)

			if not current_mesh in raw_positions:
				raw_positions[current_mesh] = []
				raw_normals[current_mesh] = []
				raw_tex_coords[current_mesh] = []
				raw_faces[current_mesh] = []

			if tok[0] == 'v':
				values = [float(v) for v in tok[1:]]
				raw_positions[current_mesh].append(tuple(values))
			elif tok[0] == 'vt':
				values = [float(v) for v in tok[1:]]
				raw_tex_coords[current_mesh].append(tuple(values))
			elif tok[0] == 'vn':
				values = [float(v) for v in tok[1:]]
				raw_normals[current_mesh].append(tuple(values))
			elif tok[0] == 'f':
				face_defs = tok[1:]
				
				for fdef in face_defs:
					fields = [int(v) if len(v) > 0 else None for v in fdef.split('/')]
					
					if len(fields) == 1: # pos pos pos ...
						pos_id = fields[0]-1

						raw_faces[current_mesh].append((pos_id-tmp_last_position_id, None, None))

						tmp_last_position_id = max(tmp_last_position_id, pos_id)
					elif len(fields) == 2: # pos/tex pos/tex pos/tex ...
						pos_id = fields[0]-1
						tex_id = fields[1]-1

						raw_faces[current_mesh].append((pos_id-last_position_id, tex_id-last_tex_coord_id, None))

						tmp_last_position_id = max(tmp_last_position_id, pos_id)
						tmp_last_tex_coord_id = max(tmp_last_tex_coord_id, tex_id)
					elif len(fields) == 3:
						if fields[1] is None: # pos//norm pos//norm pos//norm ...
							pos_id = fields[0]-1
							norm_id = fields[2]-1
							
							raw_faces[current_mesh].append((pos_id-last_position_id, None, norm_id-last_normal_id))

							tmp_last_position_id = max(tmp_last_position_id, pos_id)
							tmp_last_normal_id = max(tmp_last_normal_id, norm_id)
						else: # pos/tex/norm pos/tex/norm pos/tex/norm ...
							pos_id = fields[0]-1
							tex_id = fields[1]-1
							norm_id = fields[2]-1

							raw_faces[current_mesh].append((
								pos_id-last_position_id,
								tex_id-last_tex_coord_id,
								norm_id-last_normal_id
							))

							tmp_last_position_id = max(tmp_last_position_id, pos_id)
							tmp_last_tex_coord_id = max(tmp_last_tex_coord_id, tex_id)
							tmp_last_normal_id = max(tmp_last_normal_id, norm_id)

			elif tok[0] == 'o':
				current_mesh = tok[1].strip()
				raw_meshes.append(current_mesh)
				last_position_id = tmp_last_position_id+1
				last_tex_coord_id = tmp_last_tex_coord_id+1
				last_normal_id = tmp_last_normal_id+1
			else:
				continue

		def convert_mesh(raw_positions: list, raw_normals: list, raw_tex_coords: list, raw_faces: list):
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

		meshes: Dict[str, Mesh] = {}
		for mesh in raw_meshes:
			meshes[mesh] = convert_mesh(
				raw_positions=raw_positions[mesh],
				raw_normals=raw_normals[mesh] if mesh in raw_normals else [],
				raw_tex_coords=raw_tex_coords[mesh] if mesh in raw_tex_coords else [],
				raw_faces=raw_faces[mesh]
			)

		return meshes
