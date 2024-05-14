from typing import List
from core.node import Node
from core.timer import Timer
from core.rays_caster import CastResult, RaysCaster


class Scene(Node):
    def __init__(self, timer: Timer = None) -> None:
        super().__init__()
        self.timer: Timer = timer or Timer()
        self.rays_caster = RaysCaster()
    
    def update(self):
        self.timer.update()
        self._invoke_update(self.timer)

    def cast_rays_from_origin(self, origin, dirs):
        return self.rays_caster.cast_from_origin(origin, dirs, self.children)

    add_object = Node.bind_node