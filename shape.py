import numpy as np
from numpy import sin, cos, pi
from pygame import draw
from params import params
from util import farr, Rec

# Shape and Draw
def draw_point(screen, point, color = params.div_color):
    draw.circle(screen, color, point, params.point_radius)

class Shape:
    def __init__(self, *args, **kwargs):
        assert False # Abstract class
    #
    def draw_divs(self, screen, view, color = params.div_color):
        for div in self.divs:
            draw_point(screen, view.rtop(div), color)
    #
    def get_div(self, i):
        if self.loopy:
            return self.divs[i % len(self.divs)]
        else:
            try: return self.divs[i]
            except IndexError: return None
    ###


class Circle(Shape):
    def __init__(self, center, radius, ndivs = 120):
        self.loopy = True
        self.center = farr(center)
        self.radius = float(radius)
        def at_angle(theta):
            return center + radius * np.array([cos(theta), sin(theta)])
        # good way to do it with numpy (ie avoid list comprehension) ??
        ts = np.linspace(0.0, 2 * pi, ndivs, False)
        self.divs = np.array([at_angle(t) for t in ts])
    #
    def draw(self, screen, view, color = params.shape_color):
        pcenter, prad = view.rtop(self.center), view.rtopd(self.radius)
        draw.circle(screen, color, pcenter, prad, width = 1)
        Shape.draw_divs(self, screen, view)
    ###

class Point(Shape):
    def __init__(self, p):
        self.loopy = True
        self.p = farr(p)
        self.divs = np.array([p])
    #
    def draw(self, screen, view, color = params.shape_color):
        draw_point(screen, view.rtop(p), color)
    ###

class Line(Shape):
    def __init__(self, a, b, ndivs = 30):
        self.loopy = False
        self.a = farr(a)
        self.b = farr(b)
        self.divs = np.linspace(a, b, ndivs)
    #
    def draw(self, screen, view, color = params.shape_color):
        draw.line(screen, color, view.rtop(self.a), view.rtop(self.b))
        Shape.draw_divs(self, screen, view)
    ###

# class Weave:
#     def __init__(self, rec1, rec2, nwires):
#         # rec* = Rec(s = <shape>, start = <div_index>, incr = <num skip between>)
#         self.endpoints = (startrec, endrec)
#         self.nwires = nwires
#     #
#     def draw(self, screen, view, color = Color(128, 0, 64)):
#         def get_point(which, i):
#             rec = self.endpoints[which]
#             return rec.s.get_div(rec.start + i * rec.incr)
#         #
#         for i in range(self.nwires):
#             a = get_point(0, i)
#             b = get_point(1, i)
#             if (a is None or b is None):
#                 return
#             draw.line(screen, color, view.rtop(a), view.rtop(b))
#     ###
# 
