import numpy as np
import pygame as pg
from math import atan2

from .math_utils import dist 
from .util import take
from .params import params

eps = params.eps

def subdiv(pre, repeat = ()): return pre, repeat
def prerepeat(subdiv): return subdiv[0]
def repeat(subdiv): return subdiv[1]
#
def iter_subdiv(subdiv):
    yield from iter(prerepeat(subdiv))
    #
    if not repeat(subdiv): return
    while True: yield from iter(repeat(subdiv))
#

class Grid:
    def __init__(self):
        self.center = np.array([0, 0])
        self.phase = 0
        self.smallest_grad = 100 # pixels
        #
        self.rsubdivs = subdiv([], [2]) # r = radial
        self.asubdivs = subdiv([6], [2]) # a = arc-wise
        #
        self.fade_factor = params.grid_fade_factor
        #
        self._render = None
        self._points = np.array([]).reshape((-1, 2))
    #
    def asubdiv(self, index):
        return take( iter_subdiv(self.asubdivs), index + 1)[-1]
    #
    def rsubdiv(self, index):
        return take( iter_subdiv(self.rsubdivs), index + 1)[-1]
    #
    def update(self, view, dims):
        ar, v, tau, ph = np.array, view, 2 * np.pi, self.phase # abbrevs
        def inside(p, topleft, bottomright, margin = eps):
            # note: use small error_margin to avoid the problematic case where
            # the center is on a side of the screen. (treat as being inside instead)
            for dim in [0, 1]:
                if not (topleft[dim] - margin <= p[dim] <= bottomright[dim] + margin):
                    return False
            else: return True
        #
        corners = ar([[0, 0], [0, 1], [1, 0], [1, 1]]) * ar([x-1 for x in dims])
        corners = ar([ v.ptor(p) for p in corners])
        #
        # find rmin, rmax, tmin, tmax where:
        # rmin, rmax are the bounds of the circle ring encompassing the screen
        # tmin, tmax are the bounds (angles in [0, tau) ) of the circle sector encompassing the screen
        rmax = max( dist(self.center, corner) for corner in corners )
        if inside(self.center, corners[1], corners[2]): # 1,2 (not 0, 3) bc ptor inverts ys
            rmin = 0
            tmin, tmax = 0, tau - eps
        else:
            rmin = min( dist(self.center, corner) for corner in corners )
            rmin -= v.ptord( max(dims) / 2 ) 
            angles = sorted([ atan2(y, x) for [x, y] in corners - self.center ])
            # find which of the angles is the start one.
            # key idea: if the center is outside, the sector must be less than half a circle
            for i in range(4):
                start, end = angles[i], angles[ (i+3) % 4 ]
                if (end - start) % tau < tau / 2: 
                    tmin, tmax = start, start + (end - start) % tau
                    break
            else: assert(False)
        #
        # compute rgrads, agrads, the size of the graduations indexed by subdivision level
        grad = 1
        rgrads = []
        bound = v.ptord(self.smallest_grad)
        for d in iter_subdiv(self.rsubdivs):
            if bound > grad: break
            rgrads.append(grad)
            grad /= d
        else:
            if bound < grad: rgrads.append(grad)
        #
        arc = tau
        agrads = []
        bound = v.ptord(self.smallest_grad) / rmax * 2 # * 2 is arbitrary (looks nicer)
        for d in iter_subdiv(self.asubdivs):
            if bound > arc: break # impossible 1st time (should be)
            agrads.append(arc)
            arc /= d
        else:
            if bound < arc: agrads.append(arc)
        #
        # self.points(...), self.render(...) are wrappers around these closures
        # which capture the intermediate values. (bounds etc...)
        def first_above(low, step = 1):
            return step * np.ceil(low / step)
        #
        def render(surf, bg, fg):
            def color_lerp(t, c0, c1):
                return pg.Color( (1 - t) * ar(c0) + t * ar(c1) )
            min_fade = 1 / 20 
            #
            # note: reverse so brighter graduations get drawn above
            [x_c, y_c] = v.rtop(self.center)
            for lv, grad in reversed([*enumerate(rgrads)]):
                color = color_lerp(min_fade + (1-min_fade)*self.fade_factor ** lv, bg, fg)
                for r in np.arange(first_above(rmin, grad), rmax, grad):
                    r_pix = v.rtopd(r)
                    arc_rect = pg.Rect(x_c - r_pix, y_c - r_pix, 2 * r_pix, 2 * r_pix)
                    pg.draw.arc(surf, color, arc_rect, tmin, tmax)
            #
            for lv, arc in reversed([*enumerate(agrads)]):
                color = color_lerp(min_fade + (1-min_fade)*self.fade_factor ** lv, bg, fg)
                for angle in ph + np.arange(first_above(tmin - ph, arc), tmax - ph, arc):
                    start = self.center + rmin * ar([np.cos(angle), np.sin(angle)])
                    end = self.center + rmax * ar([np.cos(angle), np.sin(angle)])
                    pg.draw.line(surf, color, v.rtop(self.center), v.rtop(end))
        self._render = render
        #
        if not rgrads or not agrads:
            self._points = ar([]).reshape((-1, 2))
            return
        dr, dt = rgrads[-1], agrads[-1]
        r0 = first_above(rmin, dr)
        # TODO? maybe hande r = 0 (when center is inside) specially
        nrings = (rmax - r0) // dr
        if nrings < 0: nrings = 0
        #
        angles = ph + np.arange(first_above(tmin - ph, dt), tmax - ph, dt)
        units = ar([ np.cos(angles), np.sin(angles) ]).transpose()
        small_arc = self.center + r0 * units
        big_arc = self.center + (r0 + (nrings - 1) * dr) * units
        #
        self._points = np.linspace(small_arc, big_arc, int(nrings)).reshape((-1, 2))
    #
    def render(self, surf, bg, fg):
        if not self._render: return
        return self._render(surf, bg, fg)
    #
    def points(self):
        return self._points 

