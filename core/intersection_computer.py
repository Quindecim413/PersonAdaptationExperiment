import os
import numpy as np


os.environ['PYOPENCL_CTX'] = '0'
import pyopencl as cl

class IntersectionsComputer:
    def __init__(self) -> None:
        self.ctx = cl.create_some_context()
        self.queue = cl.CommandQueue(self.ctx)
        self.prog_str = """
        #define EPSILON 1e-7
        typedef struct {
            float x, y, z;
        } vec3f;

        vec3f add_vec(vec3f v1, vec3f v2){
            return (vec3f){v1.x+v2.x, v1.y+v2.y, v1.z+v2.z};
        }

        vec3f subtract_vec(vec3f v1, vec3f v2){
            return (vec3f){v1.x-v2.x, v1.y-v2.y, v1.z-v2.z};
        }

        float dot_vec(vec3f v1, vec3f v2){
            return v1.x*v2.x + v1.y*v2.y + v1.z*v2.z;
        }

        vec3f cross_vec(vec3f v1, vec3f v2){
            return (vec3f){
                    v1.y * v2.z - v1.z * v2.y,
                    v1.z * v2.x - v1.x * v2.z,
                    v1.x * v2.y - v1.y * v2.x
                };
        }

        vec3f multiply_vec(vec3f v, float a){
            return (vec3f){v.x*a, v.y*a, v.z*a};
        }

        float length_vec(vec3f v){
            return sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
        }

        //https://en.wikipedia.org/wiki/M%C3%B6ller%E2%80%93Trumbore_intersection_algorithm
        bool intersect_line_triangle(vec3f origin, vec3f ray, vec3f v0, vec3f v1, vec3f v2, vec3f * res) {

            vec3f edge1, edge2, h, s, q;
            float a, f, u, v, t;

            edge1 = subtract_vec(v1, v0);
            edge2 = subtract_vec(v2, v0);
            h = cross_vec(ray, edge2);
            a = dot_vec(edge1, h);
            if (fabs(a) < EPSILON)
                return false; // This ray is parallel to this triangle.
            
            f = 1.0/a;
            s = subtract_vec(origin, v0);
            u = f * dot_vec(s, h);
            if ((u < 0.0 + EPSILON) || (u > 1.0 - EPSILON))
                return false;

            q = cross_vec(s, edge1);
            v = f*dot_vec(ray, q);
            if ((v < 0.0 + EPSILON) || (u + v > 1.0 - EPSILON))
                return false;

            t = f * dot_vec(edge2, q); // На этом шаге рассчитывается параметр t, позволяющий определить нахождение точки пересечения на линии
            if (t > EPSILON){ // Зарегистрировано пересечение луча и треугольника
                (*res) = add_vec(origin, multiply_vec(ray, t));
                return true;
            }else{ // Имеется пересечение линии, но не луча
                return false;
            }
        }
        __kernel void compute_intersections(
            float x, float y, float z, __global const vec3f* rays,
            int n_triangles,
            __global const vec3f* v0s, __global const vec3f* v1s, __global const vec3f* v2s,
            __global vec3f* intersections, __global float* distances
        ){
            int gid = get_global_id(0);
            vec3f origin = {x, y, z};
            vec3f intersection_point;
            vec3f ray = rays[gid];
            ray = multiply_vec(ray, 1 / length_vec(ray));
            float cur_distance;
            distances[gid] = NAN;

            float min_distance = INFINITY;
            for (int j = 0; j < n_triangles; j++) {
                if (intersect_line_triangle(origin, ray, v0s[j], v1s[j], v2s[j], &intersection_point)){
                    cur_distance = length_vec(subtract_vec(intersection_point, origin));
                    if (cur_distance < min_distance) {
                        intersections[gid] = intersection_point;
                        distances[gid] = cur_distance;
                        min_distance = cur_distance;
                    }
                }
            }
        }
        """
        self.prg = cl.Program(self.ctx, self.prog_str).build()
        self.compute_intersections_knl = self.prg.compute_intersections
        self.compute_intersections_knl.set_scalar_arg_dtypes([np.float32, np.float32, np.float32, None, np.int32, None,None,None,None,None])

    def compute(self, origin, rays, v0, v1, v2):
        origin = np.array(origin, np.float32).reshape(-1, 3)
        rays = np.array(rays, np.float32)
        v0 = np.array(v0, np.float32)
        v1 = np.array(v1, np.float32)
        v2 = np.array(v2, np.float32)
        
        if not (v0.shape == v1.shape and v1.shape == v2.shape) :
            raise ValueError(f'v0, v1, v2 should have same shape to form triangle, found v0.shape={v0.shape}, v1.shape={v1.shape}, v2.shape={v2.shape}')
        if v0.ndim != 2:
            raise ValueError(f'v0, v1, v2 should be 2-dimensional, found v0.ndim={v0.ndim}')
        if v0.shape[1] != 3:
            raise ValueError(f'v0, v1, v2 are data points in 3-d space and should have 3 coordinates per each vertex, found v0.shape={v0.shape}')
        
        if rays.ndim != 2:
            raise ValueError(f'rays should be 2-dimensional, found rays.ndim={rays.ndim}')
        if rays.shape[1] != 3:
            raise ValueError(f'rays create rays in 3-d space and should have 3 coordinates per each ray, found rays.shape={rays.shape}')
        
        if origin.shape != (1,3):
            raise ValueError(f'origin should represent single point in 3d space, found origin.shape={origin.shape}')

        mf = cl.mem_flags
        cl_rays = cl.Buffer(self.ctx, mf.READ_ONLY|mf.COPY_HOST_PTR, hostbuf=rays)
        cl_v0 = cl.Buffer(self.ctx, mf.READ_ONLY|mf.COPY_HOST_PTR, hostbuf=v0)
        cl_v1 = cl.Buffer(self.ctx, mf.READ_ONLY|mf.COPY_HOST_PTR, hostbuf=v1)
        cl_v2 = cl.Buffer(self.ctx, mf.READ_ONLY|mf.COPY_HOST_PTR, hostbuf=v2)
        intersections = np.empty_like(rays, np.float32)
        distances = np.empty(len(rays), np.float32)
        cl_intersections = cl.Buffer(self.ctx, mf.WRITE_ONLY, intersections.nbytes)
        cl_distances = cl.Buffer(self.ctx, mf.WRITE_ONLY, distances.nbytes)
        
        knl_event = self.compute_intersections_knl(self.queue, (len(rays),), None, 
                            origin[0, 0], origin[0, 1], origin[0, 2], cl_rays,
                            np.int32(len(v0)),
                            cl_v0, cl_v1, cl_v2,
                            cl_intersections, cl_distances)
        cl.enqueue_copy(self.queue, intersections, cl_intersections, is_blocking=False, wait_for=[knl_event])
        cl.enqueue_copy(self.queue, distances, cl_distances, is_blocking=False, wait_for=[knl_event])
        return distances, intersections