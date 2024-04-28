import numpy as np
from math import *

from .params import params
from .util import id

eps = params.eps
tau = np.pi * 2

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
    if type(angle) == float   : sin, cos = np.sin(angle), np.cos(angle)
    if type(angle) == np.ndarray: [cos, sin] = unit(angle, noop = assume_unit) # angle is given by vector
    return ar([
        [cos, -sin],
        [sin,  cos],
    ])
    #

hz_mirror_matrix = ar([ [1, 0], [0, -1] ])
vt_mirror_matrix = ar([ [-1, 0], [0, 1] ])
def mirror_matrix(angle = 0., assume_unit = False):
    if type(angle) is float and angle == 0.: return hz_mirror_matrix
    #
    if (type(angle) == float):
        return rot_matrix(2 * angle) * hz_mirror_matrix
    elif (type(angle) == np.ndarray):
        [cos, sin] = unit(angle, noop = assume_unit)
        return rot_matrix(ar([ cos**2 - sin**2, 2*cos*sin ]), assume_unit) @ hz_mirror_matrix

def projection_matrix(dir, assume_unit = False):
    dir = unit(dir, noop = assume_unit)
    im_x = np.dot(dir, ar([1, 0])) * dir
    im_y = np.dot(dir, ar([0, 1])) * dir
    return ar([im_x, im_y]).transpose()

def angle_diff_vec(v, u, assume_unit = False):
    "return unit vector with polar angle u^v"
    [cosu, sinu] = unit(u, noop = assume_unit)
    [cosv, sinv] = unit(v, noop = assume_unit)
    return ar([ cosu*cosv + sinu*sinv, cosu*sinv - cosv*sinu ]) # trig identities

def ortho(v):
    [x, y] = v
    return ar([y, -x])

