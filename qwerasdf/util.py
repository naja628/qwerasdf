import numpy as np
from math import sqrt
import sys

def id(x): return x

def take(seq, n):
    seq = iter(seq)
    ret = []
    try:
        for _ in range(n):
            ret.append(next(seq))
    finally:
        return ret

def eprint(*a, **ka):
    ka['file'] = sys.stderr
    print(*a, **ka)

def sprint(*a, sep = ' ', end = '\n'):
    return sep.join(a) + end

def constants(n):
    return range(n)
# use case K1, K2, K3 = constants(3)

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

def clamp(x, mini, maxi):
    if x < mini: return mini
    elif x > maxi: return maxi
    else: return x

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


def do_chain(fun, *more):
    return lambda: [ fun() for fun in [fun, *more]][-1]

class EarlyExit(BaseException): pass

