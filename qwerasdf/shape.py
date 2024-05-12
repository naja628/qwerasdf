from copy import copy, deepcopy
import numpy as np
from numpy import sin, cos, pi
from pygame import draw, Color, Rect
from math import atan2

from .params import params
from .util import Rec
from .math_utils import *

def draw_point(screen, point, color = params.div_color, rad = params.point_radius):
    draw.circle(screen, color, point, rad)

class Shape:
    _KEYPOINT_NAMES = ()
    #
    def set_divs(self, ndivs):
        raise NotImplementedError()
    #####
    def __init__(self, *keypoints, ndivs = 60): # 60: arbitrary fallback
        self.keypoints = np.array([ar(p) for p in keypoints])
        self.set_divs(ndivs)
    #
    def __setattr__(self, key, val):
        try:
            i = type(self)._KEYPOINT_NAMES.index(key)
            self.keypoints[i] = ar(val)
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
    def draw(self, screen, view, color, draw_divs = True):
        # call at end of child method
        if draw_divs:
            self.draw_divs(screen, view)
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
    def _naive_merger(self, to):
        if ( type(to) != type(self) ) or ( len(self.divs) != len(to.divs) ):
            return None
        kp1, kp2 = self.keypoints, to.keypoints
        if all([ almost_equal(a, b) for a, b in zip(kp1, kp2) ]):
            return lambda i : i # same dir
        if all([ almost_equal(a, b) for a, b in zip(kp1, reversed(kp2)) ]):
            return lambda i : len(self.divs) - 1 - i # opposite dirs
        ##
    ####

def bounding_rect(shape0, *shapes):
    vmin, vmax = np.amin(shape0.divs, 0), np.amax(shape0.divs, 0)
    for sh in shapes:
        vmin = np.amin(ar([vmin, np.amin(sh.divs, 0)]), 0)
        vmax = np.amax(ar([vmax, np.amax(sh.divs, 0)]), 0)
    return vmin, vmax

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
            [x, y] = (self.other - self.center) / r
            start_angle = atan2(y, x)
            rot_dir = -1 if self.clockwise else 1
            ts = np.linspace(start_angle, start_angle + 2 * pi * rot_dir, ndivs, False)
            xs, ys = np.cos(ts), np.sin(ts)
            self.divs = self.center + r * np.array([xs, ys]).transpose()
        except ZeroDivisionError:
            self.divs = np.array([self.center] * ndivs)
    #
    def draw(self, screen, view, color = params.shape_color, draw_divs = True):
        pcenter = view.rtop(self.center)
        pradius = view.rtopd(dist(self.center, self.other))
        draw.circle(screen, color, pcenter, pradius, width = 1)
        super().draw(screen, view, color, draw_divs)
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

class Arc(Shape):
    _KEYPOINT_NAMES = ('center', 'start', 'end')
    def __init__(self, center, start, end, ndivs = 30, clockwise = False):
        center, start, end = (ar(p) for p in (center, start, end))
        self.loopy = False
        self.clockwise = clockwise
        rs, re = dist(center, start), dist(center, end)
        if near_zero(rs) or near_zero(re):
            start = end = center
        else: # make start - center and end - center be the same size
            rel = end - center
            end = center + rel * rs / re
        Shape.__init__(self, center, start, end, ndivs = ndivs)
    #
    def set_divs(self, ndivs):
        if almost_equal(self.center, self.start):
            self.divs = np.array( ndivs * [self.center] )
            return
        #
        t1, t2 = (atan2(p[1], p[0])
                  for p in (self.start - self.center, self.end - self.center))
        diff = (t2 - t1) % (2*np.pi)
        if self.clockwise:
            t1, t2 = t1, t1 + diff - (2*np.pi)
        else:
            t1, t2 = t1, t1 + diff
        rr = dist(self.center, self.start)
        #
        dts = np.linspace(t1, t2, ndivs)
        xs, ys = np.cos(dts), np.sin(dts)
        self.divs = self.center + rr * np.array([xs, ys]).transpose()
    #
    def draw(self, screen, view, color = params.shape_color, draw_divs = True):
        if almost_equal(self.center, self.start):
            Shape.draw_divs(self, screen, view)
            return
        #
        rr = dist(self.center, self.start)
        centerp, rp = view.rtop(self.center), view.rtopd(rr)
        left, top = centerp[0] - rp, centerp[1] - rp
        bound = Rect(left, top, 2 * rp, 2 * rp)
        #
        t1, t2 = (atan2(p[1], p[0])
                  for p in (self.start - self.center, self.end - self.center))
        t1, t2 = t1, t1 + ((t2 - t1) % (2*np.pi))
        if self.clockwise:
            t1, t2 = t2, t1
        #
        draw.arc(screen, color, bound, t1, t2)
        super().draw(screen, view, color, draw_divs)
    #
    def transform(self, matrix, center):
        [[a, b], [c, d]] = matrix
        det = a * d - b * c
        if det < 0: 
            self.clockwise = not self.clockwise
        return Shape.transform(self, matrix, center)
    #
    def merger(self, to):
        if ( type(to) != Arc ) or ( len(self.divs) != len(to.divs) ):
            return None
        if ( self.clockwise != to.clockwise ):
            return None
        if all([ almost_equal(p, q) for p, q in zip(self.keypoints, to.keypoints) ]):
            return lambda i : i # same dir always (determined by order)
        ##
    #

class Point(Shape):
    _KEYPOINT_NAMES = ('p')
    def __init__(self, p, ndivs = 1): # `ndivs` is a dummy
        self.loopy = True
        Shape.__init__(self, p, ndivs = 1)
    #
    def set_divs(self, ndivs):
        self.divs = np.array([self.p])
    #
    def draw(self, screen, view, color = params.shape_color, draw_divs = True):
        # draw_divs ignored
        draw_point(screen, view.rtop(self.p), color, rad = params.point_shape_radius)
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
    def draw(self, screen, view, color = params.shape_color, draw_divs = True):
        pstart, pend = view.rtop(self.start), view.rtop(self.end)
        draw.line(screen, color, pstart, pend)
        super().draw(screen, view, color, draw_divs)
    #
    def merger(self, to):
        return self._naive_merger(to)
    ###

class PolyLine(Shape):
    def __init__(self, point1, point2, *points, ndivs = 120, loopy = False):
        self.loopy = loopy
        Shape.__init__(self, point1, point2, *points, ndivs = ndivs)
    #
    def set_divs(self, ndivs):
        if ndivs == 1: 
            self.divs = np.array([self.keypoints[0]])
            return
        #
        keypoints = [*self.keypoints] + ([self.keypoints[0]] if self.loopy else [])
        kp_dists = [0]
        for i in range(len(keypoints) - 1):
            [a, b] = keypoints[i:i+2]
            kp_dists.append( kp_dists[-1] + dist(a, b) )
        #
        if near_zero(kp_dists[-1]):
            self.divs = np.array([keypoints[0]])
            return
        #
        k, D = 0, kp_dists[-1]
        ts = np.linspace(0, D, ndivs, endpoint = not self.loopy)
        divs = []
        for t in ts:
            while k + 1 < len(keypoints) and t > kp_dists[k + 1]: 
                k += 1
            segment_len = (kp_dists[k+1] - kp_dists[k])
            if near_zero(segment_len):
                t = kp_dists[k]
            else:
                t = (t - kp_dists[k]) / segment_len
            divs.append( (1. - t) * keypoints[k] + t * keypoints[k+1] )
        self.divs = np.array(divs)
    #
    def draw(self, screen, view, color = params.shape_color, draw_divs = True):
        if len(self.keypoints) == 1:
            draw_point(screen, self.keypoints[0], color)
            return
        ppoints = [view.rtop(rp) for rp in self.keypoints]
        draw.lines(screen, color, self.loopy, ppoints)
        super().draw(screen, view, color, draw_divs)
    # 
    def merger(self, to):
        # Doesn't handle rotations of keypoints
        if (type(to) != PolyLine) or not self.loopy == to.loopy:
            return None
        if (len(self.keypoints) != len(to.keypoints)):
            return None
        return self._naive_merger(to)
    ###

###### SHAPE SERIALIZATION ###########

_prefix_to_initializer = { 
        'cr' : (Circle, {'clockwise': False}),
        'ccr' : (Circle, {'clockwise': True}), 
        'ln' : (Line, {}),
        'ls' : (PolyLine, {'loopy': False}),
        'po' : (PolyLine, {'loopy': True}),
        'p' : (Point, {}),
        'ar': (Arc, {'clockwise': False}),
        'car': (Arc, {'clockwise': True})
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
        # needed because the "right" copy is "half-deep"
        [hg1, hg2] = self.hangpoints
        new_hangpoints = [Rec(s = hg1.s, i = hg1.i), Rec(s = hg2.s, i = hg2.i)]
        return Weave(new_hangpoints, self.nwires, self.incrs)
    #
    def draw(self, screen, view, color, antialias = True, width = 1):
        def get_point(which, i):
            hg = self.hangpoints[which]
            return hg.s.get_div(hg.i + i * self.incrs[which])
        #
        for i in range(self.nwires):
            a = get_point(0, i)
            b = get_point(1, i)
            if (a is None or b is None):
                return
            if width == 1 and antialias:
                draw.aaline(screen, color, view.rtop(a), view.rtop(b))
            else:
                draw.line(screen, color, view.rtop(a), view.rtop(b), width = width)
    #
    def change_dir(self):
        inc0, inc1 = self.incrs
        self.incrs = (-inc0, -inc1)
    #
