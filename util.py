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
    def set(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
            # self.__dict__[k] = v
        return self

# def non_rebinding_set(obj, other):
#     for k, v in other.__dict__.items():
#         obj.__dict__[k] = v
#     for k in obj.__dict__.keys():
#         if not k in other.__dict__:
#             del obj.__dict__[key]
