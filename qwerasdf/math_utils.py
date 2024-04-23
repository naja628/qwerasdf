import numpy as np

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

def unit(u): 
    d = dist(u, [0, 0])
    if near_zero(d): raise ZeroDivisionError
    return np.array(u) / d

