from core.node import Node
from core.transform import Transform


class VirtualCamera(Node):
    def __init__(self, transform: Transform = None) -> None:
        super().__init__(transform)

    @property
    def view_direction(self):
        self.transform.get_forward(True)
