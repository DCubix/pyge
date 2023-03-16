import pyge_import

from pygex.animation import ease_out_elastic, ease_in_out_cubic
from pygex.animation import TargetAnimator, FloatInterpolator
from pygex.rendering import Mesh, Texture2D, Shader
from pygex.vmath import Vector3, Transform, Quaternion

class Apple:
    apple_mesh: Mesh = None
    apple_tex: Texture2D = None

    IDLING = 0
    SPAWNING = 1
    SPAWNING_LOOP = 2
    EATEN = 3
    EATEN_LOOP = 4
    DEAD = 5

    def __init__(self):
        if not Apple.apple_mesh:
            Apple.apple_mesh = Mesh.from_wavefront(f'{pyge_import.assets_folder}/apple.obj')['mesh']
            Apple.apple_tex = Texture2D.from_image_file(f'{pyge_import.assets_folder}/apple.png')

        self.transform = Transform()
        self.state = Apple.SPAWNING

        self.scale_anim = TargetAnimator(FloatInterpolator(0.0, 1.0))
    
    def set_eaten(self):
        self.state = Apple.EATEN

    def draw(self, shader: Shader):
        Apple.apple_tex.bind(0)
        model = self.transform.to_matrix4()
        shader.set_uniform('uModel', *model.raw)
        Apple.apple_mesh.draw()

    def update(self, dt: float):
        self.transform.rotation *= Quaternion.from_angle_axis(3.0 * dt, Vector3(0, 1, 0))

        match self.state:
            case Apple.SPAWNING:
                self.scale_anim.interpolator.begin = 0.0
                self.scale_anim.set_target(1.0, 1.5)
                self.transform.scale = Vector3(0.0)
                self.state = Apple.SPAWNING_LOOP
            case Apple.SPAWNING_LOOP:
                v = self.scale_anim.get_value(dt, ease_out_elastic)
                self.transform.scale = Vector3(v, v, v)
                if self.scale_anim.state == TargetAnimator.FINISHED:
                    self.state = Apple.IDLING
            case Apple.EATEN:
                self.scale_anim.interpolator.begin = 1.0
                self.scale_anim.set_target(0.0, 0.3)
                self.state = Apple.EATEN_LOOP
            case Apple.EATEN_LOOP:
                v = self.scale_anim.get_value(dt, ease_in_out_cubic)
                self.transform.scale = Vector3(v, v, v)
                if self.scale_anim.state == TargetAnimator.FINISHED:
                    self.state = Apple.DEAD
            case _: pass
