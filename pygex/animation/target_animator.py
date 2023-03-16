from typing import Callable
from .animator import Animator, Interpolator

class TargetAnimator(Animator):
    def __init__(self, interpolator: Interpolator):
        super().__init__(interpolator)

    def get_value(self, delta_time: float, curve: Callable[[float], float]=None):
        match self.state:
            case Animator.RUNNING:
                t = self.time_fraction
                if curve: t = curve(t)

                self.interpolator.update(t)

                if self.time_secs < self.duration_secs:
                    self.time_secs += delta_time
                else:
                    self.interpolator.update(1.0)
                    self.time_secs = self.duration_secs
                    self.state = Animator.FINISHED
            case _: return self.interpolator.end
        return self.interpolator.value
    
    def set_target(self, target, duration: float=1.0):
        self.interpolator.begin = self.interpolator.value
        self.interpolator.end = target
        self.time_secs = 0.0
        self.duration_secs = duration
        self.state = Animator.RUNNING
