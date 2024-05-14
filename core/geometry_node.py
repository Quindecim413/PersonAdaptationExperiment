from core.mesh import TMeshCollection, TMeshEmpty
from core.node import Node
from core.transform import Transform


class GeometryNode(Node):
    def __init__(self, transform: Transform = None, meshes: TMeshCollection = None) -> None:
        super().__init__(transform)
        self.meshes = meshes or TMeshEmpty()
        self.__visible = True
    
    def is_visible(self):
        return self.__visible

    def set_visible(self, visible=True):
        self.__visible = bool(visible)