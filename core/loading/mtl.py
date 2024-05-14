from typing import List
import os

from core.material import Material

class MTL:
    def __init__(self, materials: List[Material], file_path:str=None) -> None:
        self.materials_by_names = {}
        self.file_path = file_path
        self.__materials = list(materials)

        for material in self.__materials:
            self.materials_by_names[material.name] = material
    
    @property
    def materials(self):
        return self.__materials.copy()

    @staticmethod
    def from_file(file_path):
        contents = {}
        file_dir = os.path.dirname(file_path)
        with open(file_path, "r") as f:
            for line in f:
                if line.startswith('#'): continue
                values = line.split()
                if not values: continue
                if values[0] == 'newmtl':
                    mtl_data = contents[values[1]] = {}
                elif mtl_data is None:
                    raise ValueError("mtl file doesn't start with newmtl stmt")
                elif values[0] == 'map_Kd':
                    # load the texture referred to by this declaration
                    mtl_data[values[0]] = os.path.join(file_dir, values[1])
                else:
                    mtl_data[values[0]] = tuple(map(float, values[1:]))
        
        return MTL([Material(name, content['Kd']) 
                    for name, content in contents.items()], file_path)

    def __getitem__(self, key) -> dict:
        return self.materials_by_names[key]
