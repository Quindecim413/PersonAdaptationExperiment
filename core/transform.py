import numpy as np
from scipy.spatial.transform import Rotation as R

order = 'yxz'
order_inds = {'x':list(order).index('x'), 'y':list(order).index('y'), 'z':list(order).index('z')}

def compute_matrix_update(start_mat, final_mat):
    change_mat = np.linalg.inv(start_mat) @ final_mat
    return change_mat

import math

def rotation_matrix(axis, theta):
    """
    Return the rotation matrix associated with counterclockwise rotation about
    the given axis by theta radians.
    """
    axis = np.asarray(axis)
    axis = axis / math.sqrt(np.dot(axis, axis))
    a = math.cos(theta / 2.0)
    b, c, d = -axis * math.sin(theta / 2.0)
    aa, bb, cc, dd = a * a, b * b, c * c, d * d
    bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
    return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                     [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                     [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])

def compute_ypr(matr, degrees=False):
    return R.from_matrix(matr[:3, :3]).as_euler(order, degrees=degrees)

class Transform:
    pass    

class Transform:
    def __init__(self, parent=None, tag=''):
        self._parent: Transform = None
        self.tag = tag
        self.parent: Transform = parent
        self._matrix = np.identity(4, dtype=np.float32)

    @staticmethod
    def from_position(vec, parent=None):
        tr = Transform(parent)
        tr.set_position(vec)
        return tr

    @staticmethod
    def from_matrix(mat, parent=None):
        tr = Transform(parent)
        tr.set_matrix(mat)
        return tr

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        if value is not None:
            if not isinstance(value, Transform):
                raise TypeError('parent should have TransformsNode type')
            self._parent = value
        else:
            self._parent = DefaultTransformNode()

    def reparent(self, other_transform):
        self.parent = other_transform

    def get_matrix(self, space_glob=False):
        if space_glob:
            return np.dot(self._matrix, self.parent.get_matrix(True)).astype(np.float32)
        return np.array(self._matrix, np.float32)
    
    def set_matrix(self, value, space_glob=False):
        value = np.array(value, 'float32')
        if value.shape != self._matrix.shape:
            raise ValueError(f'Invalid set matrix shape {value.shape}')
        if space_glob:
            parent_global_mat = self.parent.get_matrix(True)
            self._matrix = value @ np.linalg.inv(parent_global_mat)
        else:
            self._matrix = value
        return self

    def reset(self):
        self.set_matrix(np.identity(4, 'float32'))
        
    def get_position(self, space_glob=False):
        return self.get_matrix(space_glob)[3, :3]
    
    def set_position(self, position_vec3, space_glob=False):
        matr = np.array(self.get_matrix(space_glob))
        matr[3, :3] = position_vec3
        self.set_matrix(matr, space_glob)

    def set_scale(self, scale_vec3, space_glob=False):
        matr = np.array(self.get_matrix(space_glob))
        matr[0,0]=scale_vec3[0]
        matr[1,1]=scale_vec3[1]
        matr[2,2]=scale_vec3[2]
        self.set_matrix(matr, space_glob)
        return self

    def get_scale(self, space_glob=True):
        matr = np.array(self.get_matrix(space_glob))
        scale = np.array([matr[0,0], matr[1,1], matr[2,2]])
        return scale

    def get_rotation_mat(self, space_glob=False):
        return self.get_matrix(space_glob)[:3, :3]
    
    def set_rotation_mat(self, mat3x3, space_glob=False):
        matr = np.array(self.get_matrix(space_glob))
        matr[:3, :3] = mat3x3
        self.set_matrix(matr, space_glob)
        return self
# By convention, OpenGL is a right-handed system. What this basically says is that the positive x-axis is to your right, 
# the positive y-axis is up and the positive z-axis is backwards. 
# Think of your screen being the center of the 3 axes and the positive z-axis going through your screen towards you.

    WORLD_FORWARD = np.array([0,  0,  -1], 'float32')
    WORLD_UP      = np.array([ 0,  1,  0], 'float32')
    WORLD_RIGHT   = np.array([1, 0, 0], 'float32')
    WORLD_ORIGIN  = np.array([0, 0, 0], 'float32')

    
    def get_right(self, space_glob=False):
        matr = self.get_rotation_mat(space_glob)
        # return self.WORLD_RIGHT @ matr
        return matr[0, :3]

    def get_up(self, space_glob=False):
        matr = self.get_rotation_mat(space_glob)
        # return self.WORLD_UP @ matr
        return matr[1, :3]

    def get_forward(self, space_glob=False):
        matr = self.get_rotation_mat(space_glob)
        # return self.WORLD_FORWARD @ matr
        return -matr[2, :3]

    def get_eulers(self, degrees=True, space_glob=False):
        # https://robotics.stackexchange.com/questions/8516/getting-pitch-yaw-and-roll-from-rotation-matrix-in-dh-parameter
        matr = self.get_rotation_mat(space_glob)
        
        return R.from_matrix(matr).as_euler(order, degrees=degrees)
    
    def set_eulers(self, yaw, pitch, roll, degrees=True, space_glob=False):
        rot_mat = R.from_euler(order, [yaw, pitch, roll], degrees=degrees).as_matrix()
        self.set_rotation_mat(rot_mat, space_glob=space_glob)

    def get_yaw(self, degrees=True, space_glob=False):
        ypr = self.get_eulers(degrees, space_glob)
        return ypr[0]
    
    def get_pitch(self, degrees=True, space_glob=False):
        ypr = self.get_eulers(degrees, space_glob)
        return ypr[1]
    
    def get_roll(self, degrees=True, space_glob=False):
        ypr = self.get_eulers(degrees, space_glob)
        return ypr[2]

    def rotate_origin(self, rot_axes, angle, degrees=True, space_glob=False):
        new_rotation = np.identity(4)

        vec = angle*rot_axes
        rot = R.from_rotvec(np.deg2rad(vec) if degrees else vec)
        new_rotation[:3, :3] = rot.as_matrix()

        final_mat = np.dot(self.get_matrix(space_glob), new_rotation)
        self.set_matrix(final_mat, space_glob)
        return self
    
    def rotate(self, rot_axes, angle, degrees=True, space_glob=False):
        new_rotation = np.identity(4)
        vec = angle*rot_axes
        rot = R.from_rotvec(np.deg2rad(vec) if degrees else vec)
        new_rotation[:3, :3] = rot.as_matrix()
        new_transform = np.array(self.get_matrix(space_glob))
        new_transform[3, :3] -= self.get_position(space_glob)
        new_transform = new_transform @ new_rotation
        new_transform[3, :3] += self.get_position(space_glob)

        self.set_matrix(new_transform, space_glob)
        return self

    def move(self, delta_vec, space_glob=False):
        delta_vec = np.array(delta_vec, 'float32')
        matr = self.get_matrix(space_glob)
        matr[3, :3] += delta_vec
        self.set_matrix(matr, space_glob)
        return self

    def copy(self):
        tr = Transform(self.parent)
        tr._matrix = self._matrix
        return tr
    
    def get_relative_to(self, other_transform: Transform, space_glob=False):
        matr_origin = other_transform.get_matrix(space_glob)
        final_matr = self.get_matrix(space_glob)
        change_mat = compute_matrix_update(matr_origin, final_matr)
        
        ret = Transform()
        ret.set_matrix(change_mat)
        return ret
    


class DefaultTransformNode(Transform):
    def __init__(self):
        super().__init__(self)

    def get_matrix(self, space_glob=False):
        return np.eye(4, dtype=float)



if __name__ == '__main__':
    cam_transform = Transform()
    transform = Transform()
    # transform.rotate(np.pi/4, 0, 0)
    # transform.move([0, 0, 1])
    print(transform.get_matrix())
    for _ in range(12):
        print('----', (transform.get_position()))
        transform.rotate(yaw=np.pi/4)
        transform.move([1, 0, 0])
        
        
