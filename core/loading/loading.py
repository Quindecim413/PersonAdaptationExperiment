from typing import List
from .obj import Obj
from core.mesh import Mesh, TMeshCollection
import os
from core.loading.mtl import MTL


def load_objs(filename):
    obj = Obj('')
    objs: List[Obj] = []

    mtl: MTL = None
    v_offset = 0
    vt_offset = 0


    for line_ind, line in enumerate(open(filename, "r")):
        if line.startswith('#'): continue
        line = line.replace('\n', '')
        values = line.split()

        if not values: continue
        if values[0] == 'o':
            v_offset += len(obj.vertexes)
            vt_offset += len(obj.texcoords)

            obj_name = line[2:]
            obj = Obj(obj_name)
            objs.append(obj)
            print(obj_name)
        elif values[0] == 'v':
            obj.add_vertex(float(values[1]), float(values[2]), float(values[3]))
        elif values[0] == 'vt':
            obj.add_texcoord(float(values[1]), float(values[2]))
        elif values[0] in ('usemtl', 'usemat'):
            material_name = values[1]
            obj.start_material(mtl[material_name])
        elif values[0] == 'mtllib':
            mtl_path = os.path.join(os.path.dirname(filename), line[7:])
            mtl = MTL.from_file(mtl_path)
        elif values[0] == 'f':
            verts = values[1:]
            verts_triangulated = []
            if len(verts) == 3:
                verts_triangulated = [verts[:3]]
            else:
                for i in range(2, len(verts)):
                    verts_triangulated.append([verts[0], verts[i-1], verts[i]]) 
            for verts_set in verts_triangulated:
                face_inds = list(map(lambda ind: ind-1 - v_offset, map(int, map(lambda el: el.split('/')[0], verts_set))))
                obj.add_face(*face_inds)
                # https://www.reddit.com/r/opengl/comments/qs4wdi/parsing_an_obj_file_for_use_with_an_index_buffer/
    
    if len(objs) == 0:
        # Кейс, в котором ни разу не встретилось обозначение объекта и 
        # всё пишется в объект по умолчанию
        objs.append(obj) 

    for obj in objs:
        obj.prepare_data()
    
    return objs


def load_meshes(filepath):
    objs = load_objs(filepath)
    meshes: List[Mesh] = []
    for obj in objs:
        print('obj->Mesh',obj.name)
        mesh = Mesh(obj.vertexes, obj.faces, obj.mesh_materials, name=obj.name)
        meshes.append(mesh)
    return TMeshCollection(meshes)