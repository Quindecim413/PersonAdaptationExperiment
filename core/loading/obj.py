import numpy as np
from core.material import Material
from core.mesh import MeshMaterials


class Obj:
    def __init__(self, name):
        self.vertexes = []
        self.faces = []
        self.texcoords = []
        self.name = name
        
        self._current_material: Material = Material('default', (.8, .8, .8))
        self._current_material_range = [0, 0]
        self.materials_to_faces_inds = {self._current_material: self._current_material_range}

    def __repr__(self) -> str:
        return f'Obj({self.name})'

    __str__ = __repr__

    def add_vertex(self, x, y, z):
        self.vertexes.append((x, y, z))

    def start_material(self, material: Material):
        start_ind = len(self.faces)
        end_ind = start_ind
        self._current_material = material 
        self._current_material_range = [start_ind, end_ind]
        self.materials_to_faces_inds[material] = self._current_material_range

    def add_face(self, v1, v2, v3):
        self.faces.append((v1, v2, v3))
        self._current_material_range[1] = len(self.faces)
    
    def add_texcoord(self, u, v):
        self.texcoords.append((u,v))

    def prepare_data(self):
        self.vertexes = np.array(self.vertexes, 'float32')
        self.faces = np.array(self.faces, 'uint32')
        self.texcoords = np.array(self.texcoords, 'float32')

        self.mesh_materials = MeshMaterials()
        for material, [start, end] in self.materials_to_faces_inds.items():
            self.mesh_materials.add(material, start, end)
