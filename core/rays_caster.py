from typing import List, Tuple
from core.geometry_node import GeometryNode
from core.node import Node
from core.intersection_computer import IntersectionsComputer
import numpy as np
from dataclasses import dataclass


def walk_nodes(nodes: List[Node]):
    for node in nodes:
        yield from walk_nodes(node.children)
        yield node


@dataclass(frozen=True)
class CastResult:
    points_3d:np.ndarray
    distances:np.ndarray
    nodes:List[Node]


class RaysCaster:
    def __init__(self) -> None:
        self.intersection_computer = IntersectionsComputer()

    def cast_from_origin(self, rays_origin, rays, nodes: List[Node]):
        rays = np.array(rays, 'float32').reshape(-1, 3)

        rays_origin = np.array(rays_origin, 'float32')
        
        intersect_points = np.full([len(rays), 3], np.nan, dtype=np.float32)
        distances_final = np.full(len(rays), np.finfo(np.float32).max, dtype=np.float32)
        intersect_nodes = np.full(len(rays), None)
        
        for node in walk_nodes(nodes):
            if not isinstance(node, GeometryNode):
                continue
            mesh_matr = node.transform.get_matrix(True)
            for mesh in node.meshes:
                # compute vertexes position with transform applied in global space. perform multiplication on 4x4 matrix so 4x1 coordinates for each vertex required
                distances, intersections = self.__find_intersections_points(rays_origin, rays, mesh, mesh_matr)
                
                nans_mask = np.isnan(distances)
                distance_compare = distances < distances_final

                update_mask = ~nans_mask & distance_compare
                
                distances_final[update_mask] = distances[update_mask]
                intersect_points[update_mask] = intersections[update_mask]
                intersect_nodes[update_mask] = node

            final_nans_mask = ~np.isnan(intersect_points[:, 0])
            
        return CastResult(intersect_points[final_nans_mask], distances_final[final_nans_mask], intersect_nodes[final_nans_mask])

    def __find_intersections_points(self, rays_origin, rays, mesh, mesh_matr) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        vertexes = np.ones((mesh._vertexes.shape + np.array([0, 1])), dtype=np.float32)
        vertexes[:, :3] = mesh._vertexes
        vertexes_transformed = np.dot(vertexes, mesh_matr)[:, :3]
        v0 = vertexes_transformed[mesh._indexes[:, 0]]
        v1 = vertexes_transformed[mesh._indexes[:, 1]]
        v2 = vertexes_transformed[mesh._indexes[:, 2]]

        return self.intersection_computer.compute(rays_origin, rays, v0, v1, v2)