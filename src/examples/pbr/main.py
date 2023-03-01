import pyge_import

from pyge.application import Application
from pyge.rendering import Mesh, Shader, Texture2D, Sampler, RenderTarget, Utils, Font
from pyge.vmath import Matrix4, Vector3, Transform, Quaternion

import math, pygame, random
import numpy as np
from OpenGL.GL import *

assets = pyge_import.assets_folder

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        # Camera-related
        cam_pos = Vector3(0.0, 1.5, 3.0)
        self.camera = Transform(translation=cam_pos, rotation=Quaternion.from_look_at(cam_pos, Vector3(0.0, 0.0, 0.0)))
        self.projection = Matrix4.from_perspective(math.pi / 5, self.aspect, 0.01, 500.0)

        # Application-related
        self.rotation = 0.0
    
    def on_update(self, deltaTime: float):
        self.rotation += deltaTime

    def on_draw(self):
        glClearColor(0.0, 0.1, 0.35, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


if __name__ == '__main__':
    App().run()
