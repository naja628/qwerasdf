from pygame import *
from shape import *
from context import g
from util import dist, Rec

def post_error(msg, context = g):
    # TODO actual thing
    print(msg)

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
    return point, candidates

# Event and dispatch
_DETACHED = 0; _DONE = 1; _ATTACHED = 2; _JOINING = 3; _BAD = 4
class EvHook:
    def __init__(self, make_hook, *args, **kwargs):
        self.status = HS.DETACHED
        self.cleanup = lambda : None
        self.iter = make_hook(self, *args, **kwargs)
        assert 'watched' in self.__dict__ # should be set-up by `make_hook`
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
            match self.status:
                case _DETACHED: self.status = _DONE
                case _ATTACHED: self.status = _JOINING
                case _: self.status = _BAD
    #
    def finish(self):
        self.cleanup()
        self.watched = set()
        self.done = True
    #
    def detached(): return self.status == _DETACHED
    def done(): return self.status == _DONE
    def attached(): return self.status == _ATTACHED
    def joining(): return self.status == _JOINING
    def bad(): return self.status == _BAD
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
    def dispatch1(self, ev):
        if not ev.type in self.type_to_hook:
            return
        #
        hooks = self.type_to_hook[ev.type]
        while hooks and hooks[-1].done:
            hooks.pop()
        if not hooks:
            del self.type_to_hook[ev.type]
            return
        #
        hooks[-1].pass_ev(ev)
        if hooks[-1].joining():
            self.dispatch1(ev)
    #
    def dispatch(self, events):
        for ev in events:
            dispatch1(ev)
    ###

# Constant/Utils for pygame event linux mapping
MS_LEFT = 1
MS_MID = 2
MS_RIGHT = 3

def alpha_scan(event):
    if not 4 <= event.scancode <= 29:
        return ''
    return chr(97 + event.scancode - 4)

def click_type_is(event, evtype, button):
    return event.type == evtype and event.button == button
#
def left_click(event):
    return click_type_is(event, MOUSEBUTTONDOWN, MS_LEFT)
def mid_click(event):
    return click_type_is(event, MOUSEBUTTONDOWN, MS_MID)
def right_click(event):
    return click_type_is(event, MOUSEBUTTONDOWN, MS_RIGHT)
#
def left_unclick(event):
    return click_type_is(event, MOUSEBUTTONUP, MS_LEFT)
def mid_unclick(event):
    return click_type_is(event, MOUSEBUTTONUP, MS_MID)
def right_unclick(event):
    return click_type_is(event, MOUSEBUTTONUP, MS_RIGHT)

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

def draw_circles_hook(hook, context = g):
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    #
    def cleanup(): context.hints = []
    hook.cleanup = cleanup
    #
    def iter():
        # def get_point(pos):
        #     return context.view.ptor(pos)
        def get_circle(center, pos):
            # rpos = get_point(pos)
            rpos, _ = snappy_get_point(pos, context)
            return Circle(center, dist(center, rpos))
        #
        center = None
        while e := hook.ev:
            if left_click(e):
                if center is None:
                    # center = get_point(e.pos)
                    center, _ = snappy_get_point(e.pos)
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
        # def get_point(pos):
        #     return context.view.ptor(pos)
        def get_line(a, pos):
            # rpos = get_point(pos)
            rpos, _ = snappy_get_point(pos, context)
            return Line(a, rpos)
        #
        a = None
        while e := hook.ev:
            if left_click(e):
                if a is None:
                    # a = get_point(e.pos)
                    a, _ = snappy_get_point(pos, context)
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
    def iter():
        while e := hook.ev:
            context.view.zoom(mouse.get_pos(), factor ** e.y)
            yield
    return iter()

def create_weave_hook(hook, context = g):
    hook.watched = { MOUSEBUTTONDOWN }
    def iter():
        c, hangs, nloop = context, [None] * 3, 0
        def scroll_loop_hook(hook):
            hook.watched = {MOUSEWHEEL}
            def iter():
                nloop += hook.ev.y
                if nloop < 0: nloop = 0
            return iter()
        #
        def update_hints_hook(hook):
            hook.watched = { MOUSEMOTION }
            def iter():
                c.hints = [ Point(h.s[h.i]) for h in hangs if (h != None) ]
                under_cursor, m = snappy_get_point(hook.ev.pos, c)
                if m: c.hints.append(Point(under_cursor))
            return iter()
        #
        def get_hang():
            if not left_click(hook.ev): return 
            #
            _, matches = snappy_get_point(hook.ev.pos, c)
            if not matches: 
                post_error("no shape under cursor", c)
                return
            # for now just assume first match (TODO)
            return Rec(s = matches[0].s, start = matches[0].i)
        #####
        wheel_hook, mo_hook = None, c.dispatch.add_hook(update_hints_hook)
        def cleanup(): 
            mo_hook.finish(); c.hints = []
            if wheel_hook is not None: wheel_hook.finsh()
        hook.cleanup = cleanup
        # loop
        while True:
            for i in range(2):
                while (hangs[i] := get_hang()) is None: yield
                yield
            #
            wheel_hook = c.dispatch.add_hook(scroll_loop_hook)
            while (hangs[2] := get_hang()) is None and hangs[2].s != hangs[1].s:
                if hangs[2] is not None:
                    post_error("must belong to same shape", c)
                yield
            #
            wheel_hook.finish()
            c.weaves.append(Weave(hangs, c.weave_incrs, nloop))
            nloop, hangs = [None] * 3, 0
            continue
    return iter()
