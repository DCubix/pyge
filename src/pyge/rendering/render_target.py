from typing import List
from OpenGL.GL import *

from .texture import Texture, Texture2D

class RenderTarget:
    def __init__(self, width: int, height: int):
        id_arr = GLuint()
        glCreateFramebuffers(1, id_arr)
        self.id = id_arr

        self.size = (width, height)

        self.bind()
        glReadBuffer(GL_NONE)
        glDrawBuffer(GL_NONE)
        self.unbind()

        self.color_attachments: List[Texture] = []
        self.depth_attachment: Texture2D = None
        self.stencil_attachment: Texture2D = None

        self.render_buffer_id = None
        self.render_buffer_storage: GLenum = None

        self._tmp_target = None
        self._tmp_viewport = [0, 0, 0, 0]

    def bind(self):
        self._tmp_target = GL_FRAMEBUFFER
        self._tmp_viewport = glGetIntegerv(GL_VIEWPORT)
        glBindFramebuffer(GL_FRAMEBUFFER, self.id)
        glViewport(0, 0, self.size[0], self.size[1])
    
    def unbind(self):
        glBindFramebuffer(self._tmp_target, 0)
        glViewport(*self._tmp_viewport)

    def bind_read(self):
        self._tmp_target = GL_READ_FRAMEBUFFER
        self._tmp_viewport = glGetIntegerv(GL_VIEWPORT)
        glBindFramebuffer(GL_READ_FRAMEBUFFER, self.id)
        glViewport(0, 0, self.size[0], self.size[1])
    
    def bind_write(self):
        self._tmp_target = GL_DRAW_FRAMEBUFFER
        self._tmp_viewport = glGetIntegerv(GL_VIEWPORT)
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self.id)
        glViewport(0, 0, self.size[0], self.size[1])

    def add_color_attachment(self, tex: Texture, mip: int = 0):
        w, h = self.size
        if w != tex.size[0]:
            raise Exception('Invalid texture format. Must be the same size as the FBO.')

        if tex.dimensions >= 2 and h != tex.size[1]:
            raise Exception('Invalid texture format. Must be the same size as the FBO.')

        attachments = [ GL_COLOR_ATTACHMENT0 + i for i in range(len(self.color_attachments)+1) ]

        glNamedFramebufferTexture(self.id, attachments[-1], tex.id, mip)
        glNamedFramebufferDrawBuffers(self.id, len(attachments), attachments)

        glCheckNamedFramebufferStatus(self.id, GL_FRAMEBUFFER)

        self.color_attachments.append(tex)

    def add_depth_attachment(self):
        w, h = self.size
        tex = Texture2D(w, h, GL_DEPTH_COMPONENT24)

        glNamedFramebufferTexture(self.id, GL_DEPTH_ATTACHMENT, tex.id, 0)
        glCheckNamedFramebufferStatus(self.id, GL_FRAMEBUFFER)

        self.depth_attachment = tex
    
    def add_stencil_attachment(self):
        w, h = self.size
        tex = Texture2D(w, h, GL_R8)

        glNamedFramebufferTexture(self.id, GL_STENCIL_ATTACHMENT, tex.id, 0)
        glCheckNamedFramebufferStatus(self.id, GL_FRAMEBUFFER)

        self.stencil_attachment = tex

    def add_renderbuffer(self, internalFormat: GLenum, attachment: GLenum):
        w, h = self.size

        rbo_id = GLuint()
        glCreateRenderbuffers(1, rbo_id)

        self.render_buffer_id = rbo_id

        glNamedRenderbufferStorage(rbo_id, internalFormat, w, h)
        glNamedFramebufferRenderbuffer(self.id, attachment, GL_RENDERBUFFER, rbo_id)
        glCheckNamedFramebufferStatus(self.id, GL_FRAMEBUFFER)
