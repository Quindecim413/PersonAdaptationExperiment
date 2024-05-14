from typing import List
from core.mesh import Mesh, TMeshCollection, TMeshEmpty
from core.timer import Timer
from core.transform import Transform
from PyQt6.QtCore import QObject, pyqtSlot


class Node:
    pass

class Node(QObject):
    def __init__(self, transform: Transform = None,) -> None:
        super().__init__()
        self.transform = transform or Transform()
        self.__parent: Node = None
        self.__children: List[Node] = []
        self.__setup_done = False

    @property
    def children(self):
        return list(self.__children)

    def bind_node(self, subnode: Node):
        subnode: Node = subnode
        if subnode.__parent is not None:
            subnode.__parent.__children.remove(subnode)
        subnode.__parent = self
        subnode.transform.parent = self.transform
        self.__children.append(subnode)

    def _invoke_update(self, timer: Timer):
        for child in self.__children:
            child._invoke_update(timer)
        if not self.__setup_done:
            self.do_setup(timer)
        self.do_update(timer)

    def do_update(self, timer: Timer):
        pass

    def do_setup(self, timer: Timer):
        pass
