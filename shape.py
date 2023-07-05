import numpy as np
from numpy import sin, cos, pi
from pygame import draw, Color
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
            if i < 0: return None
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
        draw_point(screen, view.rtop(self.p), color)
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

def _compare(a, b):
    if (a < b): return -1
    if (a == b): return 0
    if (a > b): return 1
#
def _sign(x):
    return _compare(x, 0)

class Weave:
    def __init__(self, hangs, incrs = (1, 1)):
        # hang = Rec(s = <shape>, i = <div_index>, incr = <num skip between>)
        assert len(hangs) == 3
        assert hangs[1].s == hangs[2].s
        #
        self.incrs = incrs
        if (self.incrs[1] < 0):
            self.change_dir()
        #
        self.endpoints = [hg.set(incr = inc) for hg, inc in zip(hangs[:2], incrs)]
        self.nwires = (abs(hangs[2].i - hangs[1].i) + 1) // incrs[1]
        if (hangs[1].i > hangs[2].i):
            self.change_dir()
    #
    def change_dir(self):
        inc0, inc1 = self.incrs
        self.incrs = (-inc0, -inc1)
    #
    def draw(self, screen, view, color = Color(128, 0, 64)):
        def get_point(which, i):
            hg = self.endpoints[which]
            return hg.s.get_div(hg.i + i * self.incrs[which])
        #
        for i in range(self.nwires):
            a = get_point(0, i)
            b = get_point(1, i)
            if (a is None or b is None):
                return
            draw.line(screen, color, view.rtop(a), view.rtop(b))
    ###

