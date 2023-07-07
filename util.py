import numpy as np

def farr(seq):
    return np.array([float(x_i) for x_i in seq])

def dist(a, b):
    d = 0.0
    for (a_i, b_i) in zip(a, b):
        d += (b_i - a_i) ** 2
    return d ** (1/2)

class Rec:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
    #
    def set(self, other = None, /, **kwargs):
        if other:
            kwargs = other.__dict__
        #
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

def naive_scan(s, *conversions):
    def conv(i, tok): return conversions[i](tok) if conversions[i] else tok
    #
    return tuple([conv(i, tok) for (i, tok) in enumerate(s.split())])

# Seems pretty bad?
def unique_closure(decorated):
    return decorated()
# 
# Dumb Example:
#
# @unique_closure
# def count_up():
#     n, p = 0, 0
#     def closure():
#         nonlocal n, p
#         n += 1
#         return n - 1
#     return closure
