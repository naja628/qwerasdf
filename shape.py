import numpy as np
from numpy import sin, cos, pi
from pygame import draw, Color
from params import params
from util import farr, dist, Rec

def draw_point(screen, point, color = params.div_color):
    draw.circle(screen, color, point, params.point_radius)

# Forward declare 
class Circle: pass
class Line: pass
class Point: pass

class Shape:
    _CHILDREN_MAP = {'cr' : Circle, 'ln': Line, 'p': Point}
    _KEYPOINT_NAMES = []
    #
    def Create( repre ): # STATIC
        [type_id, ndiv, *xys] = repre.split()
        keypoints = [[x, y] for x, y in zip(xys[::2], xys[1::2])]
        return Shape._CHILDREN_MAP[type_id](*keypoints, ndiv = int(ndiv))
    #
    def __init__(self, *keypoints, ndivs = params.start_ndivs):
        self.keypoints = np.array([farr(p) for p in keypoints])
        self.set_divs(ndivs)
    #
    def draw(self, screen, view, color):
        raise NotImplementedError()
    #
    def set_divs(self, ndivs):
        raise NotImplementedError()
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
            return self.__dict__[key]
    #
    def __repr__(self):
        print(type(self))
        print(Line == Line)
        print(Line == type(Line((0,0), (0, 0))))
        for tid, subtype in Shape._CHILDREN_MAP.items():
            print(tid, subtype)
            print(subtype is type(self))
            if subtype is type(self):
                found = tid
                break
        else: assert False
        repre = f"{found} {len(self.divs)}"
        for p in keypoints:
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
    def transform(self, matrix, center):
        def aux(points):
            rels = points - center
            transformed = matrix @ rels.transpose()
            final = transformed + center
            return final
        self.keypoints = aux(self.keypoints)
        self.divs = aux(self.divs)
    #
    def rotate(self, angle, center):
        rot = np.array([
            [np.cos(angle), -np.sin(angle)],
            [np.sin(angle),  np.cos(angle)]
            ])
        self.transform(angle, center)
    #
    def mirror(self, center):
        S = np.array([ [-1, 0], [0, 1] ])
        self.transform(S, center)
    #
    def scale(self, ratio, center):
        self.transform(ratio * np.identity(2), center)
    ####

class Circle(Shape):
    _KEYPOINT_NAMES = ['center', 'other']
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
    _KEYPOINT_NAMES = ['p']
    def __init__(self, p):
        self.loopy = True
        Shape.__init__(self, p, ndivs = 1)
    #
    def set_divs(self, ndivs):
        self.divs = np.array([self.p])
    #
    def draw(self, screen, view, color = params.shape_color):
        draw_point(screen, view.rtop(self.p), color)
    ###

Point((0, 0))

class Line(Shape):
    _KEYPOINT_NAMES = ['start', 'end']
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

# now : easy save, + command + transformations

### Weave
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

