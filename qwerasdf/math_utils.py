import numpy as np
from .util import id

def ar(seq):
    return np.array(seq, dtype = float)

def sqdist(a, b):
    d = 0.0
    for (a_i, b_i) in zip(a, b):
        d += (b_i - a_i) ** 2
    return d

def dist(a, b):
    return sqrt(sqdist(a, b))

def near_zero(x):
    return -params.eps < x < params.eps

def almost_equal(x, y):
    return sqdist(x, y) < params.eps ** 2

def unit(u, noop=False): 
    if noop: return u
    #
    d = dist(u, [0, 0])
    if near_zero(d): raise ZeroDivisionError
    return np.array(u) / d

def rot_matrix(angle, assume_unit = False):
    match type(angle):
        case id(float): sin, cos = np.sin(angle), np.cos(angle)
        case id(np.array): [cos, sin] = unit(angle, noop = assume_unit) # angle is given by vector
    return ar([
        [cos, -sin],
        [sin,  cos],
    ])
    #

hz_mirror_matrix = ar([ [-1, 0], [0, 1] ])

def mirror_matrix(angle = 0, assume_unit = False):
    if angle == 0: return hz_mirror_matrix
    match type(angle):
        case id(float): 
            return rot_matrix(2 * angle) * hz_mirror_matrix
        case id(np.array): 
            [cos, sin] = unit(angle, noop = assume_unit)
            return rot_matrix(ar([ cos**2 - sin**2, 2*cos*sin ]), assume_unit) * hz_mirror_matrix

