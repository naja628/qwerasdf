from copy import deepcopy
import numpy as np
from numpy import sin, cos, pi
from pygame import draw, Color

import params
from util import farr, dist, Rec

def draw_point(screen, point, color = params.div_color):
    draw.circle(screen, color, point, params.point_radius)

class Shape:
    _KEYPOINT_NAMES = ()
    #
    def __init__(self, *keypoints, ndivs = params.start_ndivs):
        self.keypoints = np.array([farr(p) for p in keypoints])
        self.set_divs(ndivs)
    ## Children MUST implement:
    #
    def draw(self, screen, view, color):
        raise NotImplementedError()
    #
    def set_divs(self, ndivs):
        raise NotImplementedError()
    ## Children MAY implement:
    def _allow_transform(self, matrix): return True # TODO True iff similitude (good default)
    ## Generic functionality (MUST NOT implement)
    #
    def __setattr__(self, key, val):
        try:
            i = type(self)._KEYPOINT_NAMES.index(key)
            self.keypoints[i] = farr(val)
        except ValueError:
            self.__dict__[key] = val
    #
    def __getattr__(self, key):
        try:
            i = type(self)._KEYPOINT_NAMES.index(key)
            return self.keypoints[i]
        except ValueError:
            try:
                return self.__dict__[key]
            except KeyError: raise AttributeError(key)
    #
    def __repr__(self):
        typre = subshape_type_to_prefix(type(self))
        repre = f"{typre} {len(self.divs)}"
        for p in self.keypoints:
            repre += f" {p[0]} {p[1]}"
        return repre
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
    #
    def move(self, motion):
        # breakpoint()
        self.keypoints += motion
        self.divs += motion
        return self
    #
    def moved(self, motion):
        # breakpoint()
        return deepcopy(self).move(motion)
    #
    def transform(self, matrix, center):
        def aux(points):
            points -= center # new relative
            transformed = matrix @ points.transpose()
            # needs another transpose?
            return transformed + center
        self.keypoints = aux(self.keypoints)
        self.set_div( len(self.divs) )
        return self
    #
    def transform(self, matrix, center):
        return deepcopy(self).transform(matrix, center)
    #
#     def rotate(self, angle, center):
#         rot = np.array([
#             [np.cos(angle), -np.sin(angle)],
#             [np.sin(angle),  np.cos(angle)]
#             ])
#         self.transform(angle, center)
#     #
#     def mirror(self, center):
#         S = np.array([ [-1, 0], [0, 1] ])
#         self.transform(S, center)
#     #
#     def scale(self, ratio, center):
#         self.transform(ratio * np.identity(2), center)
    ####

class Circle(Shape):
    _KEYPOINT_NAMES = ('center', 'other')
    def __init__(self, center, other, ndivs = 120):
        self.loopy = True
        Shape.__init__(self, center, other, ndivs = ndivs)
    #
    def set_divs(self, ndivs):
        try:
            r = dist(self.center, self.other)
            [cos0, sin0] = (self.other - self.center) / r
            ### Mmmmmmmhhh trig identities :P
            def at_angle(Dtheta):
                cos_theta = cos0 * cos(Dtheta) - sin0 * sin(Dtheta)
                sin_theta = sin0 * cos(Dtheta) + cos0 * sin(Dtheta)
                return self.center + r * np.array([cos_theta, sin_theta])
            ts = np.linspace(0.0, 2 * pi, ndivs, False)
            self.divs = np.array([at_angle(t) for t in ts])
        except ZeroDivisionError:
            self.divs = np.array([center] * ndivs)
    #
    def draw(self, screen, view, color = params.shape_color):
        pcenter = view.rtop(self.center)
        pradius = view.rtopd(dist(self.center, self.other))
        draw.circle(screen, color, pcenter, pradius, width = 1)
        Shape.draw_divs(self, screen, view)
    ###

class Point(Shape):
    _KEYPOINT_NAMES = ('p')
    def __init__(self, p, ndivs = 1): # `ndivs` is a dummy
        self.loopy = True
        Shape.__init__(self, p, ndivs = 1)
    #
    def set_divs(self, ndivs):
        self.divs = np.array([self.p])
    #
    def draw(self, screen, view, color = params.shape_color):
        draw_point(screen, view.rtop(self.p), color)
    ###

class Line(Shape):
    _KEYPOINT_NAMES = ('start', 'end')
    def __init__(self, start, end, ndivs = 30):
        self.loopy = False
        Shape.__init__(self, start, end, ndivs = ndivs)
    #
    def set_divs(self, ndivs):
        self.divs = np.linspace(self.start, self.end, ndivs)
    #
    def draw(self, screen, view, color = params.shape_color):
        pstart, pend = view.rtop(self.start), view.rtop(self.end)
        draw.line(screen, color, pstart, pend)
        Shape.draw_divs(self, screen, view)
    ###

###### SHAPE SERIALIZATION ###########

_subshape_dict = {'cr' : Circle, 'ln': Line, 'p': Point}
def subshape_prefix_to_type(prefix):
    return _subshape_dict[prefix]

_prefix_dict = { ty : pre for pre, ty in _subshape_dict.items() }
def subshape_type_to_prefix(subtype):
    return _prefix_dict[subtype]

def create_shape_from_repr( repre ):
    [typre, ndivs, *xys] = repre.split()
    keypoints = [[x, y] for x, y in zip(xys[::2], xys[1::2])]
    return subshape_prefix_to_type(typre) (*keypoints, ndivs = int(ndivs))

################ WEAVE #################
# needs its own module? 
class Weave:
    def CreateFrom3(hangs, incrs = (1, 1), color_key = None, palette = {}): # STATIC
        assert len(hangs) == 3
        assert hangs[1].s == hangs[2].s
        assert incrs[1] != 0
        #
        n = (abs(hangs[2].i - hangs[1].i) + 1) // abs(incrs[1])
        if (hangs[2].i < hangs[1].i):
            inc0, inc1 = incrs
            incrs = -inc0, -inc1
        #
        return Weave(hangs[:2], n, incrs, color_key, palette)
    #
    def __init__(self, hangpoints, n, incrs = (1, 1), color_key = None, palette = {}):
        assert incrs != (0, 0)
        self.hangpoints = hangpoints
        self.nwires = n
        self.incrs = incrs
        self.color_key = color_key
        self.palette = palette
        if color_key: assert color_key in palette
    #
    def copy(self):
        [hg1, hg2] = self.hangpoints
        new_hangpoints = [Rec(s = hg1.s, i = hg1.i), Rec(s = hg2.s, i = hg2.i)]
        return Weave(new_hangpoints, self.nwires, self.incrs, self.color_key, self.palette)
    #
    def draw(self, screen, view, color = None):
        color = color or self.color()
        def get_point(which, i):
            hg = self.hangpoints[which]
            return hg.s.get_div(hg.i + i * self.incrs[which])
        #
        for i in range(self.nwires):
            a = get_point(0, i)
            b = get_point(1, i)
            if (a is None or b is None):
                return
            draw.line(screen, color, view.rtop(a), view.rtop(b))
    #
    def change_dir(self):
        inc0, inc1 = self.incrs
        self.incrs = (-inc0, -inc1)
    #
    def set_color(self, color_key, palette = None):
        self.palette = palette or self.palette
        self.color_key = color_key
    #
    def color(self):
        try:
            return self.palette[self.color_key]
        except:
            return Color(128, 0, 64) # default if fail
    ###

