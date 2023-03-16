from typing import Callable

from ..vmath import Vector3, Quaternion, scalar_lerp

class Interpolator:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end
        self.value = None

    def update(self, factor: float):
        return None

class FloatInterpolator(Interpolator):
    def __init__(self, begin: float, end: float):
        super().__init__(begin, end)
        self.value = 0.0

    def update(self, factor: float):
        self.value = scalar_lerp(self.begin, self.end, factor)
        return self.value

class Vector3Interpolator(Interpolator):
    def __init__(self, begin: Vector3, end: Vector3):
        super().__init__(begin, end)
        self.value = Vector3()

    def update(self, factor: float):
        self.value = self.begin.lerp(self.end, factor)
        return self.value

class QuaternionInterpolator(Interpolator):
    def __init__(self, begin: Quaternion, end: Quaternion):
        super().__init__(begin, end)
        self.value = Quaternion()

    def update(self, factor: float):
        self.value = self.begin.slerp(self.end, factor)
        return self.value

class Animator:
    IDLING = 0
    RUNNING = 1
    FINISHED = 2

    def __init__(self, interpolator: Interpolator):
        self.state = Animator.IDLING
        self.time_secs = 0.0
        self.duration_secs = 1.0
        self.interpolator = interpolator
    
    def get_value(self, delta_time: float, curve: Callable[[float], float]=None):
        return Interpolator()

    @property
    def time_fraction(self):
        return self.time_secs / self.duration_secs
