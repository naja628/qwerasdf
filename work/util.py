import numpy as np
from math import sqrt

import sys

def eprint(*a, **ka):
    ka['file'] = sys.stderr
    print(*a, **ka)

def sprint(*a, sep = ' ', end = '\n'):
    return sep.join(a) + end

def constants(n):
    return range(n)

def farr(seq):
    return np.array([float(x_i) for x_i in seq])

def sqdist(a, b):
    d = 0.0
    for (a_i, b_i) in zip(a, b):
        d += (b_i - a_i) ** 2
    return d

def dist(a, b):
    return sqrt(sqdist(a, b))

class Rec:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
    #
    def update(self, other = None, /, **ka):
        if other:
            ka = other.__dict__
        self.__dict__.update(ka)
        return self
    ###

def naive_scan(s, *conversions):
    def conv(i, tok): return conversions[i](tok) if conversions[i] else tok
    #
    return tuple([conv(i, tok) for (i, tok) in enumerate(s.split())])

####### DECORATORS
# (decorator(f, *a, **ka) -> wf) -> (meta(*a, **ka) -> (ret(f) -> wf))
def param_decorator(wrapped_deco):
    def meta(*a, **ka):
        return lambda f : wrapped_deco(f, *a, **ka)
    return meta
# Dumb Example:
# 
# @param_decorator
# def declaring(f, msg):
#     def wrapped(*a, **ka):
#         print(msg)
#         return f(*a, **ka)
#     return wrapped
# 
# @declaring("foo")
# def add(a, b): return a + b

def returned(decorated):
    return decorated()
# Useful for things like unique closures, fake "singletons", ...
### eg:
# @returned
# def unique_counter():
#     ref = Rec(n = 0)
#     def ret(): ref.update(n = ref.n + 1); return ref.n
#     return ret
# 

def do_chain(fun, *more):
    return lambda: [ fun() for fun in [fun, *more]][-1]

def clamp(x, mini, maxi):
    if x < mini: return mini
    elif x > maxi: return maxi
    else: return x


