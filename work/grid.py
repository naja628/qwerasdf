import numpy as np
import pygame as pg
from math import atan2

from util import dist 
from params import params

# DEBUG
from random import randint

eps = params.eps

# TODO
# * subdivs: infinite loop if repeating segment is empty
# *          stop early if reached max division
# * 

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
    # center, phase, view, dims or surface, subdiv, sm
    def __init__(self, view, surf):
        self.center = np.array([-1, 1])
        #self.center = np.array([0, 0])
        self.rsubdivs = subdiv([], [2]) # r = radial
        self.asubdivs = subdiv([6], [2]) # a = arc-wise
        self.smallest_grad = 100 # pixels
        #
        self.fade_factor = params.grid_fade_factor
        self.view = view
        self.draw_surf = surf
        self.phase = np.pi / 4
        # call update
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
        bound = v.ptord(self.smallest_grad) / rmax * 2 # * 2 is arbitrary
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
#                     pg.draw.circle(surf, color, v.rtop(self.center), v.rtopd(r), width = 1)
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
            self._points = ar([])
            return
        dr, dt = rgrads[-1], agrads[-1]
        r0 = first_above(rmin, dr)
        nrings = (rmax - r0) // dr
#         c_inside = (r0 == 0)
#         if c_inside:
#             r0 = dr
#             nrings -= 1
        #
        angles = ph + np.arange(first_above(tmin - ph, dt), tmax - ph, dt)
        units = ar([ np.cos(angles), np.sin(angles) ]).transpose()
        small_arc = self.center + r0 * units
        big_arc = self.center + (r0 + (nrings - 1) * dr) * units
        #
        self._points = np.linspace(small_arc, big_arc, int(nrings)).reshape((-1, 2))
#         if c_inside: self._points = np.concatenate(ar([[0,0]]), self._points)
    #
    def render(self, surf, bg, fg):
        return self._render(surf, bg, fg)
    #
    def points(self):
        return self._points 
    # TODO setters for subdvis (r and a), center, phase, maybe smallest_grad

#     
# 
# 
# 
# 
# 
#         def points():
#             def first_above(step, low):
#                 return step * np.ceil(low / step)
#             dr = rgrads[-1]
#             dt = agrads[-1]
#             nrings = R // dr
#             #
#             # go from polar to eucl
#             angles = np.arange(0, 2 * np.pi - params.eps, dt)
#             units = ar([np.cos(angles), np.sin(angles)]).transpose()
#             first_ring = dr * units
#             last_ring = nrings * dr * units
#             points = np.linspace(first_ring, last_ring, int(nrings)).reshape((-1, 2)) # index 0 is [0, 0]
#             points = np.concatenate( ar([[0, 0]]) , points) + self.center
#             #
#             # filter within surf
#             bounds = ar([ v.ptor([0, 0]), v.ptor(dims) ])
#             T = points.transpose()
#             xs, ys = T[0], T[1]
#             afilter = (bounds[0][0] <= xs) & (xs <= bounds[1][0])
#             afilter &= (bounds[1][1] <= ys) & (ys <= bounds[0][1]) # inverted because corner is down
#             return points[afilter]
# 
# 
# 
# 
# 
# 
# 
# 
# 
#     def _compute(self):
#         ar = np.array
#         v, dims = self.view, self.draw_surf.get_size()
#         #
#         corners = v.corner + ar([[0.0, 0], [0, 1], [1, 0], [1, 1]]) * ar(dims)
#         corners = ar([v.ptor(p) for p in corners])
#         R = max( dist(self.center, corner) for corner in corners)
#         #
#         grad = 1
#         rgrads = []
#         bound = v.ptord(self.smallest_grad)
#         for d in iter_subdiv(self.rsubdivs):
#             rgrads.append(grad)
#             grad /= d
#             if bound > grad: break
#         else:
#             rgrads.append(grad)
#         #
#         arc = 2 * np.pi
#         agrads = []
#         bound = v.ptord(self.smallest_grad) / R
#         for d in iter_subdiv(self.asubdivs):
#             agrads.append(arc)
#             arc /= d
#             if bound > arc: break
#         else:
#             agrads.append(arc)
#         #
#         return R, rgrads, agrads
#     #
#     def render(self, bg, fg):
#         ar = np.array
#         v, surf, dims = self.view, self.draw_surf, self.draw_surf.get_size()
#         def color_lerp(t, c0, c1):
#             return pg.Color( (1 - t) * ar(c0) + t * ar(c1) )
#         #
#         dims = surf.get_size()
#         R, rgrads, agrads = self._compute()
#         #
#         for lv, gr in reversed([*enumerate(rgrads)]):
#             color = color_lerp(lv / len(rgrads), fg, bg) # TODO linear or exponential colors fading? (linear for now)
#             for r in np.arange(gr, R, gr):
#                 pg.draw.circle(surf, color, v.rtop(self.center), v.rtopd(r), width = 1)
# #         for lv, d in reversed([*enumerate(rsubdivs)]):
# #             # note: we redraw over higher levels in lower, not optimal but eh
# #             color = color_lerp(lv / len(rsubdivs), fg, bg) # TODO linear or exponential colors fading? (linear for now)
# #             for r in np.arange(grad, R, grad):
# #                 pg.draw.circle(surf, color, v.rtop(self.center), v.rtopd(r), width = 1)
# #             grad /= d
#         #
#         for lv, arc in reversed([*enumerate(agrads)]):
#             color = color_lerp(lv / len(agrads), fg, bg) # TODO linear or exponential colors fading? (linear for now)
#             for angle in np.arange(0, 2 * np.pi - params.eps, arc):
#                 end = R * ar([np.cos(angle), np.sin(angle)])
#                 pg.draw.line(surf, color, v.rtop(self.center), v.rtop(end))
#     #
#     def points(self):
#         ar = np.array
#         v, dims = self.view, draw_surf.dims
#         #
#         R, rgrads, agrads = self._compute()
#         dr = rgrads[-1]
#         dt = agrads[-1]
#         nrings = R // dr
#         #
#         # go from polar to eucl
#         angles = np.arange(0, 2 * np.pi - params.eps, dt)
#         units = ar([np.cos(angles), np.sin(angles)]).transpose()
#         first_ring = dr * units
#         last_ring = nrings * dr * units
#         points = np.linspace(first_ring, last_ring, int(nrings)).reshape((-1, 2)) # index 0 is [0, 0]
#         points = np.concatenate( ar([[0, 0]]) , points) + self.center
#         #
#         # filter within surf
#         bounds = ar([ v.ptor([0, 0]), v.ptor(dims) ])
#         T = points.transpose()
#         xs, ys = T[0], T[1]
#         afilter = (bounds[0][0] <= xs) & (xs <= bounds[1][0])
#         afilter &= (bounds[1][1] <= ys) & (ys <= bounds[0][1]) # inverted because corner is down
#         return points[afilter]
# 
