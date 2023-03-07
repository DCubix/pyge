from typing import Tuple

import pygame, time
from pygame import Surface
from pygame.event import Event

from OpenGL.GL import *

class Application:
    """Base application adapter. Your game should inherit from it."""

    def setup(self, title: str='Application', size: Tuple[int, int]=(640, 480), opengl: bool=False):
        pygame.init()

        if opengl:
            pygame.display.gl_set_attribute(pygame.GL_RED_SIZE, 8)
            pygame.display.gl_set_attribute(pygame.GL_GREEN_SIZE, 8)
            pygame.display.gl_set_attribute(pygame.GL_BLUE_SIZE, 8)
            pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
            pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
            pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 6)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 8)

        flags = (pygame.OPENGL | pygame.DOUBLEBUF) if opengl else 0
        self.display: Surface = pygame.display.set_mode(size=size, flags=flags)

        if opengl:
            # glEnable(GL_DEPTH_TEST)
            # glEnable(GL_CULL_FACE)
            glEnable(GL_MULTISAMPLE)
            glEnable(GL_TEXTURE_CUBE_MAP_SEAMLESS)

        pygame.display.flip()
        pygame.display.set_caption(title)

    def run(self, frameCap=60):
        timeStep = 1.0 / frameCap
        startTime = time.perf_counter()
        unprocessed = 0

        self.on_start()

        running = True
        while running:
            canRender = False
            currentTime = time.perf_counter()
            delta = currentTime - startTime
            startTime = currentTime
            unprocessed += delta

            for event in pygame.event.get():
                self.on_event(event)
                if event.type == pygame.QUIT:
                    running = self.on_exit()

            while unprocessed >= timeStep:
                unprocessed -= timeStep
                self.on_update(timeStep)
                canRender = True

            if canRender:
                self.on_draw()
                pygame.display.flip()

        pygame.quit()

    @property
    def aspect(self):
        return self.display.get_width() / self.display.get_height()

    @classmethod
    def on_start(self):
        pass

    @classmethod
    def on_event(self, event: Event):
        pass

    @classmethod
    def on_update(self, deltaTime: float):
        pass

    @classmethod
    def on_draw(self):
        pass

    @classmethod
    def on_exit(self):
        return False
