from copy import copy, deepcopy

import numpy as np
from numpy import sin, cos, pi
from pygame import draw, Color
from math import atan2

import params
from util import farr, dist, Rec, sqdist

def near_zero(x):
    return -params.eps < x < params.eps

def almost_equal(x, y):
    return sqdist(x, y) < params.eps ** 2

def draw_point(screen, point, color = params.div_color):
    draw.circle(screen, color, point, params.point_radius)

class Shape:
    _KEYPOINT_NAMES = ()
    #
    def draw(self, screen, view, color):
        raise NotImplementedError()
    #
    def set_divs(self, ndivs):
        raise NotImplementedError()
    #####
    def __init__(self, *keypoints, ndivs = params.start_ndivs):
        self.keypoints = np.array([farr(p) for p in keypoints])
        self.set_divs(ndivs)
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
        typre = subshape_to_prefix(self)
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
        self.keypoints += motion
        self.divs += motion
        return self
    #
    def moved(self, motion):
        return deepcopy(self).move(motion)
    #
    def transform(self, matrix, center):
        def aux(points):
            points -= center
            points = points.transpose()
            points = (matrix @ points).transpose()
            points += center 
            return points
        self.keypoints = aux(self.keypoints)
        self.set_divs( len(self.divs) )
        return self
    #
    def transformed(self, matrix, center):
        return deepcopy(self).transform(matrix, center)
    #
    def merger(self, to):
        '''if `self` and `to` intuitively "overlap", 
        retun f: i -> j, from indices on `self` to `to`
        else: return None
        '''
        return None
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
    def __init__(self, center, other, ndivs = 120, clockwise = False):
        self.loopy = True
        self.clockwise = clockwise
        Shape.__init__(self, center, other, ndivs = ndivs)
    #
    def set_divs(self, ndivs):
        try:
            r = dist(self.center, self.other)
            if near_zero(r): raise ZeroDivisionError
            [cos0, sin0] = (self.other - self.center) / r
            ### Mmmmmmmhhh trig identities :P
            def at_angle(Dtheta):
                cos_theta = cos0 * cos(Dtheta) - sin0 * sin(Dtheta)
                sin_theta = sin0 * cos(Dtheta) + cos0 * sin(Dtheta)
                return self.center + r * np.array([cos_theta, sin_theta])
            rot_dir = -1 if self.clockwise else 1
            ts = np.linspace(0.0, 2 * pi * rot_dir, ndivs, False)
            self.divs = np.array([at_angle(t) for t in ts])
        except ZeroDivisionError:
            self.divs = np.array([self.center] * ndivs)
    #
    def draw(self, screen, view, color = params.shape_color):
        pcenter = view.rtop(self.center)
        pradius = view.rtopd(dist(self.center, self.other))
        draw.circle(screen, color, pcenter, pradius, width = 1)
        Shape.draw_divs(self, screen, view)
    #
    def transform(self, matrix, center):
        [[a, b], [c, d]] = matrix
        det = a * d - b * c
        if det < 0: self.clockwise = not self.clockwise
        return Shape.transform(self, matrix, center)
    #
    def merger(self, to):
        n = len( self.divs)
        if type(to) != Circle:
            return None
        if not almost_equal(self.center, to.center):
            return None
        if n != len( to.divs ):
            return None
        if not near_zero(sqdist(self.center, self.other) - sqdist(to.center, to.other)):
            return None
        #
        def angle(u, v):
            t1, t2 = ( atan2(p[1], p[0]) for p in (u, v) )
            return t2 - t1
        phi = angle(self.other - self.center, to.other - to.center)
        delta = 2 * pi / n
        q, r = (phi + delta / 2) // delta, (phi + params.eps / 2) % delta # + delta / 2: rounding problems
        if (not near_zero(r)):
            return None
        else:
            def merger(i):
                return int(-q + (-1 if self.clockwise != to.clockwise else 1) * i) % n
            return merger
    #
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
    #
    def merger(self, to):
        if (type(to) != Point):
            return None
        if (not almost_equal(self.p, to.p)):
            return None
        return (lambda i: 0)
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
    #
    def merger(self, to):
        if ( type(to) != Line ) and ( len(self.divs) != len(to.divs) ):
            return None
        if ( almost_equal(self.start, to.start) and almost_equal(self.end, to.end) ):
            return lambda i : i # same dir
        if ( almost_equal(self.start, to.end) and almost_equal(self.end, to.start) ):
            return lambda i : len(self.divs) - 1 - i # opposite dirs
        ##
    ###

class PolyLine(Shape):
    def __init__(self, point1, *points, ndivs = 120, loopy = False):
        self.loopy = loopy
        Shape.__init__(self, point1, *points, ndivs = ndivs)
    #
    def _compute_len(self):
        self.len = sum([dist(a, b) for a, b in zip(self.keypoints[:-1], self.keypoints[1:])])
        if self.loopy:
            self.len += dist(self.keypoints[-1], self.keypoints[0])
    #
    def set_divs(self, ndivs):
        if not hasattr(self, 'len'):
            self._compute_len()
        #
        if ndivs == 1: 
            self.divs = np.array([self.keypoints[0]])
            return
        if near_zero(self.len):
            self.divs = np.array(ndivs * [self.keypoints[0]])
            return
        #
        offset, divs = 0, []
        spacing = self.len / (ndivs - 1)
        n = len(self.keypoints)
        for i in range(n + int(self.loopy) - 1):
            seglen = dist(self.keypoints[i], self.keypoints[(i + 1) % n])
            if near_zero(seglen): 
                continue
            #
            dir_vec = 1.0 / seglen * (self.keypoints[(i + 1) % n] - self.keypoints[i])
            new_divs = [ self.keypoints[i] + t * dir_vec
                    for t in np.arange(offset, seglen, spacing) ]
            divs.extend(new_divs)
            #
            r = (seglen - offset) % spacing
            offset = spacing - r
        if len(divs) == ndivs - 1:
            divs.append(self.keypoints[0] if self.loopy else self.keypoints[-1])
        assert len(divs) == ndivs
        self.divs = np.array(divs)
    #
    def draw(self, screen, view, color = params.shape_color):
        if len(self.keypoints) == 1:
            draw_point(screen, self.keypoints[0], color)
            return
        ppoints = [view.rtop(rp) for rp in self.keypoints]
        draw.lines(screen, color, self.loopy, ppoints)
        Shape.draw_divs(self, screen, view)
    # 
    ###

###### SHAPE SERIALIZATION ###########

_prefix_to_initializer = { 
        'cr' : (Circle, {'clockwise': False}),
        'ccr' : (Circle, {'clockwise': True}), 
        'ln' : (Line, {}),
        'ls' : (PolyLine, {'loopy': False}),
        'po' : (PolyLine, {'loopy': True}),
        'p' : (Point, {}),
        }

def subshape_prefix_to_initializer(prefix):
    return _prefix_to_initializer[prefix]

_subtype_to_prefix_candidates = { ini[0] : [] for ini in _prefix_to_initializer.values() }
for pre, (ty, ka) in _prefix_to_initializer.items():
    _subtype_to_prefix_candidates[ ty ].append( (pre, ka) )
#

def is_subdict(sub, sup, values_must_match = True):
    for k, v in sub.items():
        if not k in sup: return False
        if values_must_match and sup[k] != v: return False
    return True


def subshape_to_prefix(subshape):
    candidates = _subtype_to_prefix_candidates[ type(subshape) ]
    for pre, ka in candidates:
        if is_subdict(ka, subshape.__dict__):
            return pre
    else: assert False

def create_shape_from_repr( repre ):
    [typre, ndivs, *xys] = repre.split()
    keypoints = [[x, y] for x, y in zip(xys[::2], xys[1::2])]
    Ty, ka = subshape_prefix_to_initializer(typre)
    return  Ty(*keypoints, ndivs = int(ndivs), **ka)

################ WEAVE #################
# needs its own module? 
class Weave:
    def CreateFrom3(hangs, incrs = (1, 1), nloops = 0): # STATIC
        assert len(hangs) == 3
        assert hangs[1].s == hangs[2].s
        assert incrs[1] != 0
        #
        sh2 = hangs[1].s
        if sh2.loopy:
            if hangs[2].i < hangs[1].i:
                hangs[2].i += len(sh2.divs)
            hangs[2].i += nloops * len(sh2.divs)
        #
        n = (abs(hangs[2].i - hangs[1].i)) // abs(incrs[1]) + 1
        if (hangs[2].i < hangs[1].i):
            inc0, inc1 = incrs
            incrs = -inc0, -inc1
        #
        return Weave(hangs[:2], n, incrs)
    #
    def BackWeave(forward):
        n = forward.nwires - 1
        if n <= 0:
            return None
        hgs = [copy(hg) for hg in forward.hangpoints]
        #hgs[0].i += hgs[0].s.get_div(hgs[0].i + forward.incrs[0])
        sh0 = hgs[0].s
        hgs[0].i = hgs[0].i + forward.incrs[0]
        if hgs[0].i > len(sh0.divs):
            if sh0.loopy:
                hgs[0].i %= len(sh0.divs)
            else:
                return None
        return Weave(hgs, n, forward.incrs)
    #
    def __init__(self, hangpoints, n, incrs = (1, 1)):
        assert incrs != (0, 0)
        self.hangpoints = hangpoints
        self.nwires = n
        self.incrs = incrs
    #
    def copy(self):
        #needed be the "right" copy is "half-deep"
        [hg1, hg2] = self.hangpoints
        new_hangpoints = [Rec(s = hg1.s, i = hg1.i), Rec(s = hg2.s, i = hg2.i)]
        return Weave(new_hangpoints, self.nwires, self.incrs)
    #
    def draw(self, screen, view, color):
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
