from core.geometry_node import GeometryNode
from core.mesh import Mesh
from core.node import Node
from core.transform import Transform
from core.loading.loading import load_meshes
import os

class Notebook(GeometryNode):
    def __init__(self) -> None:
        super().__init__(meshes=load_meshes(os.path.join(os.path.dirname(__file__), 'notebook.obj')))
    
    @property
    def screen_vertices(self):
        verts = self.meshes['Screen'].vertexes
        rot = self.transform.get_rotation_mat(True)
        tr = self.transform.get_position(True)
        verts = verts @ rot + tr[None, :]
        return {
            'ru': verts[0],
            'rb': verts[1],
            'lu': verts[3],
            'lb': verts[2]
        }