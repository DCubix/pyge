from __future__ import annotations

from typing import List

from ..vmath import Transform, Matrix4
from ..rendering.renderer import Renderer


class GameObject:
    def __init__(self):
        self._initialized = False
        self._dead = False
        self._life = None

        self.transform = Transform()
        
        self._parent_transform = Matrix4()

        self._parent: GameObject = None
        self._children: List[GameObject] = []

        self._children_to_add: List[GameObject] = []

    def reset(self):
        self.set_parent(None)
        self._children.clear()
        self.transform = Transform()
        self._life = None
        self._dead = False
        self._initialized = False

    def add_child(self, obj: GameObject):
        if obj in self._children:
            return
        self._children.append(obj)
        obj.set_parent(self)

    def remove_child(self, obj: GameObject):
        if obj not in self._children:
            return
        obj._life = 0.0

    def set_parent(self, obj: GameObject):
        if self._parent:
            self._parent.remove_child(self)
        obj.add_child(self)
        self._parent = obj

    def destroy(self, time_out: float=0):
        self._life = time_out

    @property
    def own_transform(self) -> Matrix4:
        xform = self.transform.to_matrix4()
        return self.parent_transform * xform

    @property
    def parent_transform(self) -> Matrix4:
        if self._parent and self._parent.transform.has_changed():
            self._parent_transform = self._parent.own_transform
        return self._parent_transform

    @property
    def parent(self):
        return self._parent

    def update(self, delta_time: float):
        if self._life and isinstance(self._life, float):
            self._life -= delta_time
            if self._life <= 0.0:
                self._life = 0.0
                self._dead = True
                self.on_destroy()
        else:
            self._dead = False
        
        if self._dead:
            self.set_parent(None)
            return

        if not self._initialized:
            self.on_create()
            self._initialized = True
        self.on_update(delta_time)

        # process children
        for child in self._children:
            child.update(delta_time)

        # remove the dead
        children_to_remove = [ c for c in self._children if c._dead ]
        for child in children_to_remove:
            child._parent = None
            self._children.remove(child)
    
    def render(self, renderer: Renderer):
        self.on_render(renderer)
        
        # process children
        for child in self._children:
            child.render(renderer)

    def on_create(self):
        pass

    def on_destroy(self):
        pass

    def on_update(self, delta_time: float):
        pass

    def on_render(self, renderer: Renderer):
        pass
