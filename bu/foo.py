from pygame import *
from math import *
import numpy as np
from enum import Enum

# syntactic sugar hack
class Rec:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
    #
    def set(self, **kwargs):
        for k, v in kwargs.items():
            self.__dict__[k] = v
    ###

# pseudo-conf
conf = Rec()
conf.point_radius = 2
conf.div_color = Color(128, 128, 128)
conf.shape_color = Color(0, 128, 128)
conf.snap_radius = 4
conf.eps = 0.01

# make sure g is accessible everywhere
g = Rec() # global "scope"

def snappy_get_point(pos, context = g):
    c = context # shorter to write
    rrad = c.view.ptord(conf.snap_radius)
    shortest = rrad + conf.eps
    point = c.view.ptor(pos)
    candidates = []
    for s in c.shapes:
        for i in range(len(s.divs)):
            div = div[i]
            if (d := dist(div, c.view.ptor(pos))) < min(rrad, shortest):
                shortest = d
                point = div
            if dist(point, div) < conf.eps:
                candidates.append(Rec(s = s, i = i))
    # filter candidates
    candidates = [cd for cd in candidates if dist(cd.s, point) < conf.eps]
    return Rec(point = point, matches = candidates)

# utils
def farr(seq):
    return np.array([float(x_i) for x_i in seq])

def dist(a, b):
    d = 0.0
    for (a_i, b_i) in zip(a, b):
        d += (b_i - a_i) ** 2
    return d ** (1/2)

# View and Scaling
class View:
    def __init__(self, corner = (0,0), ppu = 500):
        self.corner = farr(corner)
        self.ppu = int(ppu)
    #
    def __str__(self):
        return f"View: \n\tcorner = {self.corner}\n\tppu = {self.ppu}\n"
    #
    def ptor(self, pp):
        "pixel to real"
        (px, py) = pp
        rx = self.corner[0] + px / self.ppu
        ry = self.corner[1] - py / self.ppu
        return farr((rx, ry))
    #
    def rtop(self, rp):
        "real to pixel"
        (rx, ry) = rp
        px = int((rx - self.corner[0]) * self.ppu)
        py = -int( (ry - self.corner[1]) * self.ppu )
        return (px, py)
    #
    def ptord(self, pd):
        return pd / self.ppu
    #
    def rtopd(self, rd):
        return int(rd * self.ppu)
    #
    def rzoom(self, rcenter, factor):
        d = self.corner - rcenter
        self.corner = rcenter + (1 / factor) * d
        self.ppu *= factor
    #
    def zoom(self, pcenter, factor):
        self.rzoom(self.ptor(pcenter), factor)
    #
    def rmove(self, rmotion):
        self.corner += rmotion
    #
    def move(self, pmotion):
        self.rmove( self.ptor(pmotion) )
    ###

# Shape and Draw
def draw_point(screen, point, color = conf.div_color):
    draw.circle(screen, color, point, conf.point_radius)

class Shape:
    def __init__(self, *args, **kwargs):
        assert False # Abstract class
    #
    def draw_divs(self, screen, view, color = conf.div_color):
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
    def draw(self, screen, view, color = conf.shape_color):
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
    def draw(self, screen, view, color = conf.shape_color):
        draw_point(screen, view.rtop(p), color)
    ###

class Line(Shape):
    def __init__(self, a, b, ndivs = 30):
        self.loopy = False
        self.a = farr(a)
        self.b = farr(b)
        self.divs = np.linspace(a, b, ndivs)
    #
    def draw(self, screen, view, color = conf.shape_color):
        draw.line(screen, color, view.rtop(self.a), view.rtop(self.b))
        Shape.draw_divs(self, screen, view)
    ###

class Weave:
    def __init__(self, rec1, rec2, nwires):
        # rec* = Rec(s = <shape>, start = <div_index>, incr = <num skip between>)
        self.endpoints = (startrec, endrec)
        self.nwires = nwires
    #
    def draw(self, screen, view, color = Color(128, 0, 64)):
        def get_point(which, i):
            rec = self.endpoints[which]
            return rec.s.get_div(rec.start + i * rec.incr)
        #
        for i in range(self.nwires):
            a = get_point(0, i)
            b = get_point(1, i)
            if (a is None or b is None):
                return
            draw.line(screen, color, view.rtop(a), view.rtop(b))
    ###

# Event and dispatch
class EvHook:
    def __init__(self, make_hook, *args, **kwargs):
        self.cleanup = lambda : None
        self.iter = make_hook(self)
        assert 'watched' in self.__dict__ # should be set-up by `make_hook`
        self.done = False
        # self.ret = None
    #
    def pass_ev(self, event):
        assert event.type in self.watched
        self.ev = event
        try:
            next(self.iter)
        except StopIteration:
            self.finish()
    #
    def finish(self):
        self.cleanup()
        self.watched = set()
        self.done = True
    ###

class EvDispatch: # event dispatcher
    def __init__(self):
        self.type_to_hook = {}
    #
    def add_hook(self, make_hook, *args, **kwargs):
        new_hook = EvHook(make_hook, *args, **kwargs)
        for type_ in new_hook.watched:
            try:
                self.type_to_hook[type_].append(new_hook)
            except KeyError:
                self.type_to_hook[type_] = [new_hook]
        return new_hook
    #
    def dispatch(self, events):
        for ev in events:
            if not ev.type in self.type_to_hook:
                continue
            #
            hooks = self.type_to_hook[ev.type]
            while hooks and hooks[-1].done:
                hooks.pop()
            if not hooks:
                del self.type_to_hook[ev.type]
                continue
            #
            hooks[-1].pass_ev(ev)
    ###

# pygame event codes for linux
MS_LEFT = 1
MS_MID = 2
MS_RIGHT = 3

def alpha_scan(event):
    if not 4 <= event.scancode <= 29:
        return ''
    return chr(97 + event.scancode - 4)

# SHIFT = 2
# CTRL = 64

# Hooks
def menu_dispatch_hook(hook, context = g):
    # F -> draw: F line, D circle
    # G -> reset
    # X -> Cancel
    hook.watched = { KEYUP }
    #
    def iter():
        menu_path = ""
        top_hook = None
        def reset_hook():
            if top_hook is None: return
            else: top_hook.finish()
        while e := hook.ev:
            print("got menu:", alpha_scan(e))
            match menu_path, alpha_scan(e): 
                case "", 'f':
                    menu_path = "f"
                case "f", 'f':
                    reset_hook()
                    top_hook = g.dispatch.add_hook(draw_lines_hook)
                case "f", 'd':
                    reset_hook()
                    top_hook = g.dispatch.add_hook(draw_circles_hook)
                case _, 'g':
                    reset_hook()
                    menu_path = ""
                case _, 'x': # TODO rethink this
                    reset_hook()
                    menu_path = menu_path[:-1] if menu_path else ""
                case _:
                    pass
            yield
    return iter()

# def create_weave_hook(hook, context = g):
#     hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
#     #
#     # TODO mousehweel thing (half_loops)
#     def cleanup(): context.hints = []
#     hook.cleanup() = cleanup
#     #
#     def iter():
#         c = context
#         n_half_loops = 0
#         hangs = [None] * 3
#         hint = None
#         def ignore():
#             return ev.type == MOUSEBUTTONDOWN and e.button != MS_LEFT
#         def get_hang():
#             if ignore():
#                 return None
#             #
#             p, matches = snappy_get_point(pos, c)
#             if not matches:
#                 return None
#             # for now just assume first match (TODO)
#             hang = Rec(s = matches[0].s, start = matches[0].i)
#             if hook.ev.type == MOUSEMOTION:
#                 hint = hang
#                 return None
#             else:
#                 return hang
# 
#         for i in range(3):
#             while (hangs[i] := get_hang()) is None:
#                 set_hints()
#                 yield
#             if i == 2:
#                 break
#             yield
#         if (hangs[1].i > hangs[2].i):
#             hangs[1:] = hangs[2], hangs[1]
#         for i in (0, 1):
#             hangs[i].set(incr = c.weave_incrs[i])
#         nwires = hangs[2].i - hangs[1].i + 1 // hangs[1].incr
#         c.weaves.append(hangs[0], hangs[1], nwires)
#         continue
# 

def draw_circles_hook(hook, context = g):
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    #
    def cleanup(): context.hints = []
    hook.cleanup = cleanup
    #
    def iter():
        def get_point(pos):
            return context.view.ptor(pos)
        def get_circle(center, pos):
            rpos = get_point(pos)
            return Circle(center, dist(center, rpos))
        #
        center = None
        while e := hook.ev:
            if e.type == MOUSEBUTTONDOWN and e.button == MS_LEFT:
                if center is None:
                    center = get_point(e.pos)
                else:
                    context.shapes.append(get_circle(center, e.pos))
                    context.hints = []
                    center = None
            elif e.type == MOUSEMOTION and center is not None:
                context.hints = [get_circle(center, e.pos)]
            yield
    return iter()

# looks very duplicated (TODO ?)
def draw_lines_hook(hook, context = g):
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    #
    def cleanup(): context.hints = []
    hook.cleanup = cleanup
    #
    def iter():
        def get_point(pos):
            return context.view.ptor(pos)
        def get_line(a, pos):
            rpos = get_point(pos)
            return Line(a, rpos)
        #
        a = None
        while e := hook.ev:
            if e.type == MOUSEBUTTONDOWN and e.button == MS_LEFT:
                if a is None:
                    a = get_point(e.pos)
                else:
                    context.shapes.append(get_line(a, e.pos))
                    context.hints = []
                    a = None
            elif e.type == MOUSEMOTION and a is not None:
                context.hints = [get_line(a, e.pos)]
            yield
    return iter()

def zoom_hook(hook, factor = 1.1, context = g):
    hook.watched = { MOUSEWHEEL }
    #
    def iter():
        while e := hook.ev:
            context.view.zoom(mouse.get_pos(), factor ** e.y)
            yield
    return iter()

# TODO move_view_hook?

def g_init():
    "init pygame and set-up globals"
    global g
    init()
    g.screen = display.set_mode((1000, 1000))
    g.clock = time.Clock()
    g.shapes = []
    g.hints = [] 
    g.view = View()
    g.dispatch = EvDispatch()
    g.weave_incrs = (1, 1)
    #g.weave_colors = []

def main():
    g_init()
    running = True
    g.dispatch.add_hook(zoom_hook)
    g.dispatch.add_hook(menu_dispatch_hook)
    while running:
        if event.get(QUIT):
            quit()
            return
        g.dispatch.dispatch(event.get())
        g.screen.fill( (0,0,0) )
        for s in g.shapes:
            s.draw(g.screen, g.view)
        for s in g.hints:
            s.draw(g.screen, g.view, color = Color(128, 32, 32))
        display.flip()
        g.clock.tick(60);
    quit()

# Run
main()
exit()

# Debug / info
def print_ev(types):
    init()
    screen = display.set_mode((100, 100)) # whatev
    clock = time.Clock()
    running = True
    while running:
        events = event.get()
        for e in events:
            if e.type == QUIT:
                running = False
            if e.type in types:
                print(e)
        clock.tick(60)
    quit()

# TODO: maybe make hooks cancellable (set some cleanup fun in *_hook?)

# class EvHook:
#     def __init__(self, hook, *args, **kwargs):
#         self.iter = make_iter(self, *args, **kwargs)
#         next(self.iter)
#         print("EvHook:", self, self.__dict__)
#     #
#     def pass_ev(self, event):
#         if not event.type in self.watched:
#             return set()
#         oldwatched = self.watched
#         self.ev = event
#         try:
#             next(self.iter)
#         except StopIteration:
#             self.watched = set()
#         return self.watched - oldwatched
#     #
#     def set_status(self, watched = None, pass_down = None):
#         if watched != None:
#             self.watched = watched
#         if pass_down != None:
#             self.pass_down = pass_down
#     ###
# 
# class EvDispatch: # event dispatcher
#     def __init__(self):
#         self.type_to_hook = {}
#     #
#     def map_hook(self, types, hook):
#         for evtype in types:
#             try:
#                 self.type_to_hook[evtype].append(hook)
#             except KeyError:
#                 self.type_to_hook[evtype] = [hook]
#     #
#     def add_hook(self, make_iter, *args, **kwargs):
#         new_hook = EvHook(make_iter, *args, **kwargs)
#         self.map_hook(new_hook.watched, new_hook)
#         return new_hook
#     #
#     def dispatch(self, events):
#         def rev_range(seq):
#             # note: can't use negative indices so we can `del` as we go down
#             return range(len(seq) - 1, -1, -1)
#         for ev in events:
#             if not ev.type in self.type_to_hook:
#                 continue
#             #
#             hooks = self.type_to_hook[ev.type]
#             for i in rev_range(hooks): # need index to `del` stuff
#                 if not ev.type in hooks[i].watched:
#                     del hooks[i] # ok bc we're going down
#                     continue
#                 #
#                 new_watched = hooks[i].pass_ev(ev)
#                 self.map_hook(new_watched, hooks[i])
#                 #
#                 if not hooks[i].pass_down:
#                     break
#             #
#             if not hooks:
#                 del self.type_to_hook[ev.type]
#     ###

# def draw_circle_hook(hook, context = g):
#     yield hook.set_status(watched = { MOUSEBUTTONDOWN }, pass_down = True)
#     #
#     while (e := hook.ev).button != MS_LEFT:
#         yield
#     center = context.view.ptor(e.pos)
#     yield hook.set_status( {MOUSEBUTTONDOWN, MOUSEMOTION}, False)
#     #
#     while e:= hook.ev :
#         if e.type == MOUSEBUTTONDOWN and e.button != MS_LEFT:
#             yield hook.set_status(pass_down = True)
#         #
#         perim_point = context.view.ptor(e.pos)
#         c = Circle(center, dist(center, perim_point))
#         if e.type == MOUSEMOTION:
#             context.hints = [c]
#             yield hook.set_status(pass_down = False)
#         elif e.type == MOUSEBUTTONDOWN:
#             context.shapes.append(c)
#             context.hints = []
#             return hook.set_status(pass_down = False)
#     ###
