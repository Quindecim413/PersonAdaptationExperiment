from collections import defaultdict
from threading import Lock
from typing import DefaultDict, List, Tuple
import numpy as np
from core.material import Material
from core.transform import Transform
from OpenGL.GL import *


class MeshMaterials:
    def __init__(self) -> None:
        self.__material2faces: DefaultDict[Material, List[Tuple[int, int]]] = defaultdict(list)

    def add(self, material: Material, face_ind_start: int, face_ind_end: int):
        if face_ind_end <= face_ind_start:
            return
        self.__material2faces[material].append((int(face_ind_start), int(face_ind_end)))

    @property
    def materials(self):
        return list(self.__material2faces.keys())

    def replace(self, old_material:Material, new_material:Material):
        if old_material not in self.__material2faces:
            raise LookupError(f'MeshMaterials does not contain {old_material}')
        material_faces = self.__material2faces.get(old_material)
        del self.__material2faces[old_material]
        self.__material2faces[new_material] = material_faces
    
    def replace_by_name(self, old_material_name:str, new_material:Material):
        found_instance = list(filter(lambda material: material.name == old_material_name, self.__material2faces))
        if not found_instance:
            raise LookupError(f'MeshMaterials does not contain material named {old_material_name}')
        self.replace(found_instance[0], new_material)

    def get_face_ranges(self, material: Material):
        return self.__material2faces[material]
    
    def __iter__(self):
        return iter(self.materials)


class Mesh:
    def __init__(self, vertexes, indexes, materials: MeshMaterials, uvs=None, name="", static=True):
        # vertex состоят из 3-х коордиат точек в простарнстве
        self._vertexes = np.array(vertexes, 'float32')
        self._uvs = np.array(uvs, 'float32')
        self._indexes = np.array(indexes, 'int32')
        self.__name: str = name
        self.static: bool = static
        self.materials = materials
        self.__vertexes_changed_id = 0

        assert self._vertexes.ndim == self._indexes.ndim == 2, 'vertex and indexes should be in 2d matrix form'
        assert len(self._vertexes) > 0, ' Element should not be empty'
        
        if not(0 <= self._indexes.min() and self._indexes.min() < len(self._vertexes)):
            raise ValueError(f'triangle vertex index can only be in range({0},{len(self._vertexes)})(min and max inds of vertices array)')
        
        self.vao = None
        self.vbo = None
        self.ebo = None

        self.__data_loaded = False
        self.__load_data_lock = Lock()
        self.__bounded = False
        self.__glvertex_last_changed_id = None

    @property
    def name(self):
        return self.__name

    @property
    def indexes(self):
        return self._indexes

    @property
    def vertexes_changed_ind(self):
        return self.__vertexes_changed_id

    @property
    def vertexes(self):
        return self._vertexes
    
    def locale_uv(self, u: float, v, float):
        pass

    @vertexes.setter
    def vertexes(self, new_vertexes):
        if self.static:
            raise AttributeError('Attempt to modify vertexes of static mesh')

        new_vertexes = np.array(new_vertexes, 'float32')
        assert self._vertexes.shape == new_vertexes.shape, 'new vertexes should have same shape as when initialized'
        self._vertexes[:] = new_vertexes
        self.__vertexes_changed_id += 1

    def __hash__(self) -> int:
        return id(self._vertexes)
    
    def load_data_to_ogl(self):
        with self.__load_data_lock:
            if self.__data_loaded:
                raise ValueError("Mesh.__data_loaded already set to True. Can't reload data to ogl")
            self.vao = glGenVertexArrays(1)
            glBindVertexArray(self.vao)
            self.vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
            glBufferData(GL_ARRAY_BUFFER, self._vertexes.nbytes, self._vertexes, GL_STATIC_DRAW if self.static else GL_DYNAMIC_DRAW)
            
            glEnableVertexAttribArray(0)
            # x, y, z  coordinates
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))

            self.ebo = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, self._indexes.nbytes, self._indexes, GL_STATIC_DRAW)

            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindVertexArray(0)
            self.__data_loaded = True

    def __try_update_vertexes_buffer(self):
        if self.__glvertex_last_changed_id != self.vertexes_changed_ind:
            self.__glvertex_last_changed_id = self.vertexes_changed_ind
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
            glBufferData(GL_ARRAY_BUFFER, self._vertexes.nbytes, self._vertexes, GL_STATIC_DRAW if self.static else GL_DYNAMIC_DRAW)
            
            glEnableVertexAttribArray(0)
            # x, y, z  coordinates
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))

    def draw(self, mode=GL_TRIANGLES):
        if self.__bounded == False:
            raise Exception('GLMesh is not binded')
        self.__try_update_vertexes_buffer()

        glDrawElements(mode, self._indexes.size, GL_UNSIGNED_INT, None)

    def draw_material(self, material: Material):
        if self.__bounded == False:
            raise Exception('GLMesh is not binded')
        self.__try_update_vertexes_buffer()

        material_ranges = self.materials.get_face_ranges(material)
        for start, end in material_ranges:
            inds_draw_count = self._indexes[start:end].size
            inds_before_nbytes = self._indexes[:start].nbytes
            glDrawElements(GL_TRIANGLES, inds_draw_count, GL_UNSIGNED_INT, ctypes.c_void_p(inds_before_nbytes))

    def bind(self):
        if not self.__data_loaded:
            self.load_data_to_ogl()
        glBindVertexArray(self.vao)
        self.__bounded = True

    def unbind(self):
        glBindVertexArray(0)
        self.__bounded = False
    
    def __enter__(self):
        self.bind()
        return self
    
    def __exit__(self, *args):
        self.unbind()

    def __del__(self):
        self.free()

    def free(self):
        pass
    
class TMeshCollection:
    def __init__(self, meshes: List[Mesh]) -> None:
        self.__meshes = list(meshes)
    
    def get_by_name(self, name: str):
        name = str(name)
        found = [m for m in self.__meshes if m.name==name]
        if found:
            return found[0]
        else:
            return None
        
    def get_by_index(self, index: int):
        index = int(index)
        return self.__meshes[index]
    
    def __iter__(self):
        return iter(self.__meshes.copy())

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.get_by_name(key)
        else:
            return self.get_by_index(key)


class TMeshEmpty(TMeshCollection):
    def __init__(self) -> None:
        super().__init__([])