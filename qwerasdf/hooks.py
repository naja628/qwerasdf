import pygame as pg

from .params import params
from .shape import *
from .view import View
from .menu import Menu
from .miniter import miniter_exec
from .context import *
from .util import param_decorator, clamp
from .merge import merge_into # TODO restructure module
from .math_utils import *
from . import save

######### EVENT AND DISPATCH ##########
class EvHook:
    def __init__(self, make_hook, *a, **ka):
        self.attached = []
        self.watched = set()
        self.cleanup = lambda: None
        #
        self.filter = None
        self.dispatch = None
        #
        self.ev_loop = None
        self.iter_filter = lambda ev: False
        self.ev_iter = None
        #
        make_hook(self, *a, **ka)
    #
    def event_loop(self, event_loop):
        self.ev_loop = event_loop
    #
    def event_iter(self, event_iter, filter = lambda ev: True):
        self.ev_iter = event_iter
        self.iter_filter = filter
        next(self.ev_iter)
    #
    def call_once(self, ev):
        assert ev.type in self.watched
        #
        if self.iter_filter(ev) and self.ev_iter:
            try: self.ev_iter.send(ev)
            except StopIteration: self.finish()
        elif self.ev_loop:
            self.ev_loop(ev)
    #
    def attach(self, sub):
        # attached hook "terminate" by calling their `cleanup` function 
        # when parent is finished
        self.attached.append(sub)
    #
    def finish(self):
        for subhook in self.attached:
            subhook.finish()
        self.watched = set()
        self.cleanup()
    #
    # status predicates:
    def active(self): return self.watched != set()
    def finished(self): return not self.active()
    
class EvDispatch: # event dispatcher
    def __init__(self):
        self.callstacks = {}
    #
    def track_hook(self, hook):
        for evtype in hook.watched:
            try:
                self.callstacks[evtype].append(hook)
            except KeyError:
                self.callstacks[evtype] = [hook]
        return hook
    #
    def add_hook(self, make_hook, *a, **ka):
        hook = EvHook(make_hook, *a, **ka) 
        hook.dispatch = self
        self.track_hook(hook)
        return hook
    #
    def all_watched(self):
        return set(self.callstacks.keys())
    #
    def dispatch(self, events):
        for ev in events:
            if not ev.type in self.callstacks:
                continue
            # filter out finished
            hooks = self.callstacks[ev.type]
            hooks = [hk for hk in hooks if hk.active()]
            #
            if hooks: 
                self.callstacks[ev.type] = hooks
                for hk in reversed(hooks):
                    if (not hk.filter) or (hk.filter(ev)):
                        hk.call_once(ev);
                        break
            else: 
                del self.callstacks[ev.type]
        #
    ###

# Hook type decorators
@param_decorator
def loop_hook(f, watched, cleanup = None, setup = None):
    def hook_maker(hook, *a, **ka):
        setup_hook(hook, watched)
        if cleanup: hook.cleanup = lambda: cleanup(*a, **ka)
        state = setup and setup(hook, *a, **ka)
        #
        def inner(ev):
            if state: f(hook, ev, *a, _state = state, **ka) 
            else: f(hook, ev, *a, **ka)
        hook.event_loop(inner)
    return hook_maker

@param_decorator
def iter_hook(f, watched, filter = lambda ev: True, cleanup = None):
    def hook_maker(hook, *a, **ka):
        if cleanup: hook.cleanup = lambda: cleanup(*a, **ka)
        setup_hook(hook, watched)
        hook.event_iter( f(hook, *a, **ka), filter)
    return hook_maker

## Pygame event related utils

# TODO probably OS dependent (Works on windows and Linux so far so maybe not ?)
MS_LEFT, MS_MID, MS_RIGHT = 1, 2, 3

ms = Rec()
ms.LCLICK, ms.MCLICK, ms.RCLICK, ms.LUNCLICK, ms.MUNCLICK, ms.RUNCLICK, ms.MOTION, ms.WHEEL = range(8)
def mouse_subtype(ev):
    button = getattr(ev, 'button', None)
    if (ev.type, button) == (pg.MOUSEBUTTONDOWN, MS_LEFT):  return ms.LCLICK
    if (ev.type, button) == (pg.MOUSEBUTTONDOWN, MS_MID):   return ms.MCLICK
    if (ev.type, button) == (pg.MOUSEBUTTONDOWN, MS_RIGHT): return ms.RCLICK
    if (ev.type, button) == (pg.MOUSEBUTTONUP, MS_LEFT):    return ms.LUNCLICK
    if (ev.type, button) == (pg.MOUSEBUTTONUP, MS_MID):     return ms.MUNCLICK
    if (ev.type, button) == (pg.MOUSEBUTTONUP, MS_RIGHT):   return ms.RUNCLICK
    if ev.type           == pg.MOUSEMOTION:                 return ms.MOTION
    if ev.type           == pg.MOUSEWHEEL:                  return ms.WHEEL
    return ev.type # if not a mouse subtype return raw pygame type
        
def alpha_scan(event):
    if not pg.KSCAN_A <= event.scancode < pg.KSCAN_A + 26:
        return event.key
    return chr(ord('A') + event.scancode - pg.KSCAN_A)

## GENERIC 
def setup_hook(hook, watched, *cleanup_commands):
    hook.watched = watched
    if cleanup_commands:
        def cleanup():
            for command in cleanup_commands:
                (fun, *a) = command
                fun(*a)
        hook.cleanup = cleanup
    #

def steal_menu_keys(hook, menu, stolen, labels):
    hook.watched.add(pg.KEYDOWN)
    def filter(ev):
        return (ev.type != pg.KEYDOWN) or ( type(key := alpha_scan(ev)) is str and key in stolen )
    hook.filter = filter
    #
    sv_stolen, sv_labels = menu.temp_show_mask, menu.temp_show
    menu.temporary_display(stolen, labels)
    break_recursion = hook.cleanup
    hook.cleanup = lambda: [menu.temporary_display(sv_stolen, sv_labels), 
                            break_recursion and break_recursion()]

## HOOKS

_AUTOSAVE = pg.event.custom_type()
# Rewind
def _autosave_setup(hook, context):
    pg.time.set_timer(_AUTOSAVE, params.autosave_pulse * 1000)
@loop_hook(  {_AUTOSAVE}, 
             cleanup = lambda: pg.time.set_timer(_AUTOSAVE, 0),
             setup = _autosave_setup )
def autosave_hook(hook, ev, context):
    if context.autosaver: context.autosaver.savepoint(context)

LOOP = pg.event.custom_type()  # TODO where should this be declared for cleaner?
@loop_hook({pg.MOUSEBUTTONDOWN, pg.MOUSEWHEEL, LOOP})
def rewind_hook(hook, ev, context):
    type = mouse_subtype(ev)
    if not context.autosaver:
        post_error("not connected to a session", context)
        hook.finish()
    elif type == ms.WHEEL:
        context.autosaver.rewind(-ev.y)
    elif type == LOOP:
        loaded_data = context.autosaver.load_current(context)
        if loaded_data: load_to_context(context, loaded_data)
    elif type == ms.LCLICK or type == ms.RCLICK:
        reset_menu(context)
        hook.finish()

def undo_n(context, n = 1):
    if not context.autosaver:
        post_error("not connected to a session", context)
        return
    #
    context.autosaver.rewind(n)
    loaded_data = context.autosaver.load_current(context)
    if loaded_data: load_to_context(context, loaded_data)
    reset_menu(context)

# Camera Control
@loop_hook({pg.MOUSEWHEEL})
def zoom_hook(hook, ev, context, factor = params.zoom_factor):
    context.view.zoom(pg.mouse.get_pos(), factor ** ev.y)
    redraw_weaves(context)

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            filter = lambda ev: mouse_subtype(ev) == ms.RCLICK )
def click_move_hook(hook, context):
    def move_view(pos):
        v = context.view
        v.corner += rstart - v.ptor(pos)
        redraw_weaves(context)
    #
    while True:
        pstart, rstart = None, None
        #
        ev = yield
        pstart, rstart = ev.pos, context.view.ptor(ev.pos)
        hook.event_loop(lambda ev: move_view(ev.pos))
        #
        ev = yield
        hook.event_loop(None)
        move_view(ev.pos)
    #

@iter_hook({ pg.MOUSEBUTTONDOWN })
def change_view_hook(hook, context):
    hook.attach(context.dispatch.add_hook(zoom_hook, context))
    hook.attach(context.dispatch.add_hook(click_move_hook, context))
    # filter HAS TO be set up here because it's the general one, not the iter one
    hook.filter = lambda ev: mouse_subtype(ev) == ms.LCLICK
    #
    ev = yield # Terminate on first event (ie LCLICK = done)


# Create Shapes
def _evpos(context, ev): return snappy_get_point(context, ev.pos)[0]

@loop_hook({pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, lambda context: reset_hints(context))
def create_points_hook(hook, ev, context):
    point = Point(_evpos(context, ev))
    match mouse_subtype(ev):
        case ms.MOTION: set_hints(context, point)
        case ms.LCLICK: create_shapes(context, point)

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
            cleanup = lambda context: reset_hints(context) )
def create_lines_hook(hook, context):
    def _Line(*a, **ka): return Line(*a, **ka, ndivs = context.df_divs['line'])
    #
    while True:
        start = None
        hook.event_loop( lambda ev: set_hints(context, Point(_evpos(context, ev))) )
        #
        ev = yield
        start = _evpos(context, ev)
        hook.event_loop( lambda ev: set_hints(context, _Line(start, _evpos(context, ev))) )
        #
        ev = yield
        create_shapes(context, _Line(start, _evpos(context, ev)))
        reset_hints(context)

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
            cleanup = lambda context: reset_hints(context) )
def create_circles_hook(hook, context):
    def _Circle(p1, p2):
        if center_first: return Circle(p1, p2, ndivs = context.df_divs['circle'])
        else: return Circle(p2, p1, ndivs = context.df_divs['circle'])
    #
    def evloop(ev):
        nonlocal center_first
        if mouse_subtype(ev) == ms.RCLICK: 
            center_first = not center_first
        set_hints(context, _Circle(point1, _evpos(context, ev)))
    #
    while True:
        point1, center_first = None, True
        hook.event_loop( lambda ev: set_hints(context, Point(_evpos(context, ev))) )
        #
        ev = yield
        point1 = _evpos(context, ev)
        hook.event_loop(evloop)
        #
        ev = yield
        create_shapes(context, 
                _Circle(point1, _evpos(context, ev) ),
                Point(point1 if center_first else _evpos(context, ev)))
        reset_hints(context)

# @iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
#             filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
#             cleanup = lambda context: reset_hints(context) )
# def create_arcs_hook(hook, context):
#     def _Arc(*a, **ka): return Arc(*a, **ka, ndivs = context.df_divs['arc'])
#     def _Circle(*a, **ka): return Circle(*a, **ka, ndivs = context.df_divs['arc'])
#     #
#     cx, clockwise, subloop = context, False, None
#     def loop(ev):
#         nonlocal clockwise
#         if mouse_subtype(ev) == ms.RCLICK:
#             clockwise = not clockwise
#         if subloop: subloop(ev)
#     hook.event_loop(loop)
#     #
#     while True:
#         subloop = lambda ev: set_hints(cx, Point(_evpos(cx, ev)))
#         ev = yield
#         center = _evpos(cx, ev)
#         #
#         subloop = lambda ev: set_hints(cx, _Circle(center, _evpos(cx, ev)))
#         ev = yield
#         start = _evpos(cx, ev)
#         #
#         subloop = lambda ev: set_hints(cx, _Arc(center, start, _evpos(cx, ev), clockwise = clockwise))
#         ev = yield
#         end = _evpos(cx, ev)
#         #
#         create_shapes(cx, _Arc(center, start, end, clockwise = clockwise))
# 
@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
            cleanup = lambda context: reset_hints(context) )
def create_arcs_hook(hook, context):
    def _Arc(*a, **ka): return Arc(*a, **ka, ndivs = context.df_divs['arc'])
    def _Circle(*a, **ka): return Circle(*a, **ka, ndivs = context.df_divs['arc'])
    def _Line(*a, **ka): return Line(*a, **ka, ndivs = context.df_divs['arc'])
    #
    center_first, clockwise = True, False
    cx, points = context, []
    def loop_first2(ev):
        nonlocal center_first
        if mouse_subtype(ev) == ms.RCLICK:
            center_first = not center_first
        #
        _points = points + [_evpos(cx, ev)]
        match _points, center_first:
            case [one], _:
                set_hints(cx, Point(one))
            case [center, perim], True:
                set_hints(cx, _Circle(center, perim))
            case [start, end], False:
                set_hints(cx, _Line(start, end))
            case _: assert False
    #
    def make_arc(*points):
        if center_first: 
            [center, start, end] = points
        else: 
            [start, end, center] = points
            # center = orthogonal projection TODO
        return _Arc(center, start, end, clockwise = clockwise)
    #
    def loop_last(ev):
        nonlocal clockwise
        if mouse_subtype(ev) == ms.RCLICK:
            clockwise = not clockwise
        #
        set_hints(cx, make_arc(*points, _evpos(cx, ev)))
    #
    while True:
        hook.event_loop(loop_first2)
        for i in range(2):
            ev = yield
            points.append(_evpos(cx, ev))
        #
        print(f'{points=}')
        hook.event_loop(loop_last)
        ev = yield
        points.append(_evpos(cx, ev))
        #
        create_shapes(cx, make_arc(*points))
        points = []

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            cleanup = lambda context: reset_hints(context) )
def create_poly_hook(hook, context):
    def _Poly(*a, **ka): return PolyLine(*a, **ka, ndivs = context.df_divs['poly'])
    points, new = [], False
    #
    def reset():
        points.clear()
        reset_hints(context)
    #
    while True:
        ev = yield
        pos = _evpos(context, ev)
        # TODO implement extra snap thing instead?
        if points and sqdist(pos, points[0]) < context.view.ptord(params.snap_radius) ** 2:
            pos = points[0]
        match mouse_subtype(ev):
            case ms.LCLICK:
                if points and (pos == points[0]).all():
                    create_shapes(context, _Poly(*points, loopy = True))
                    reset()
                else:
                    points.append(_evpos(context, ev))
            case ms.RCLICK:
                if not points: continue
                create_shapes(context, _Poly(*points, loopy = False))
                reset()
            case _:
                if not points: continue
                set_hints(context, _Poly(*points, pos, loopy = False))
    ###

# Weaves
@iter_hook( { pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION },
            filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
            cleanup = lambda context: reset_hints(context))
def create_weaves_hook(hook, context):
    cx = context
    steal_menu_keys(hook, cx.menu, 'AS', {'A': "invert dir", 'S': "invert spin"})
    dirctrl = Rec(code = 2, spin = 1, dir = 0) # maintain code = 2 * spin + dir, masks style
    subloop = None # will be set to lambda that sets proper hints
    def evloop(ev):
        match mouse_subtype(ev):
            case pg.KEYDOWN:
                key = alpha_scan(ev)
                if key == 'A': dirctrl.dir = not dirctrl.dir
                if key == 'S': dirctrl.spin = not dirctrl.spin
                dirctrl.code = dirctrl.spin * 2 + dirctrl.dir
            case ms.RCLICK:
                code = (dirctrl.code + 1) % 4
                dirctrl.update(code = code, spin = code // 2, dir = code % 2)
        if subloop: 
            try: subloop(ev)
            except: pass
    hook.event_loop(evloop)
    #
    def filter_cdt(hangs, shapes):
        return [hg for hg in hangs if hg.s in shapes]
    def get_hang():
        nonlocal subloop
        candidates = []
        while (not candidates):
            ev = yield
            _, candidates = snappy_get_point(cx, ev.pos)
            if not candidates: post_error("no shape under cursor", cx)
        while True:
            match candidates:
                case [hg]: return hg
                case []: assert False
                case cdt: 
                    post_info("several shapes match. LCLICK on wanted shape -> disambiguate", cx)
                    def disambiguated(ev):
                        _, cdt2 = snappy_get_point(cx, ev.pos)
                        try: 
                            [ hg ] = filter_cdt(cdt, [hg.s for hg in cdt2])
                            return hg
                        except: return None
                    save_loop = subloop
                    subloop = lambda ev: (hg := disambiguated(ev)) and set_hints(cx, hg.s)
                    while True:
                        ev = yield
                        if ret := disambiguated(ev): break
                        else: continue
                    subloop = save_loop
                    return ret
    #
    while True:
        subloop = lambda ev: set_hints(cx, Point(_evpos(cx, ev)))
        hg1 = yield from get_hang()
        def line_hint(ev):
            start = hg1.s.get_div(hg1.i)
            set_hints(cx, Line(start, _evpos(cx, ev), ndivs = 1))
        subloop = line_hint
        hg2 = yield from get_hang()
        def weaves_at_pos(pos):
            _, candidates = snappy_get_point(cx, pos)
            try: [ hg3 ] = [ hg for hg in candidates if hg.s == hg2.s ]
            except: return ()
            #
            incrs = cx.weavity[0] * (-1 if dirctrl.dir else 1), cx.weavity[1]
            nloops = dirctrl.spin - 1
            we = Weave.CreateFrom3([hg1, hg2, hg3], incrs, nloops)
            #
            if cx.weaveback and (bwe := Weave.BackWeave(we)): return we, bwe 
            else: return (we, )
        subloop = lambda ev: set_hints(cx, *weaves_at_pos(ev.pos))
        wes = None
        while not wes:
            ev = yield
            wes = weaves_at_pos(ev.pos)
        [create_weave(cx, we) for we in wes]
        reset_hints(cx)
    ###

@iter_hook(set(), filter = lambda ev: alpha_scan(ev) in 'QWERASDF')
def select_color_hook(hook, context):
    save_show_palette = context.show_palette
    context.show_palette = True
    #
    def cleanup(): context.show_palette = save_show_palette
    hook.cleanup = cleanup
    steal_menu_keys(hook, context.menu, 'QWERASDF', {})
    #
    ev = yield
    context.color_key = alpha_scan(ev)

# TODO kinda ugly maybe refactor
def _color_picker_setup(hook, context):
    save_show_palette = context.show_palette
    state = Rec(save_color = context.palette[context.color_key], lum = 0.7)
    #
    def cleanup(): 
        context.show_palette = save_show_palette
        context.show_picker = False
        context.palette[context.color_key] = state.save_color
    hook.cleanup = cleanup
    steal_menu_keys(hook, context.menu, context.palette.keys(), {})
    #
    context.show_palette = True
    context.show_picker = True
    return state
@loop_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION, pg.MOUSEWHEEL, _AUTOSAVE}, # suppress autosaves
            setup = _color_picker_setup)
def color_picker_hook(hook, ev, context, *, _state):
    cx = context
    if ev.type == pg.MOUSEWHEEL:
        _state.lum += params.brightness_scroll_speed * ev.y
        _state.lum = clamp(_state.lum, 0, 1)
    try: cur_color = Color(0,0,0).lerp(cx.color_picker.at_pixel(ev.pos), _state.lum)
    except: cur_color = None
    match mouse_subtype(ev), cur_color:
        case ms.RCLICK, _: hook.finish()
        case pg.KEYDOWN, _:
            cx.palette[cx.color_key] = _state.save_color
            cx.color_key = alpha_scan(ev)
            _state.save_color = cx.palette[cx.color_key]
        case _, None: pass
        case ms.LCLICK, color:
            cx.palette[cx.color_key] = color
            _state.save_color = color
        case _, color:
            cx.palette[cx.color_key] = color
    redraw_weaves(cx)

# Selection 
@loop_hook({ pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION }, lambda context: reset_hints(context))
def select_hook(hook, ev, context):
        cur_pos, matches = snappy_get_point(context, ev.pos)
        shapes = [ m.s for m in matches ]
        match mouse_subtype(ev):
            case ms.LCLICK:
                context.selected = shapes
            case ms.RCLICK:
                keep = [sh for sh in context.selected if not sh in shapes]
                add = [sh for sh in shapes if not sh in context.selected]
                context.selected = keep + add
            case ms.MOTION:
                set_hints(context, *shapes)

## TRANSFORMATIONS
def copy_weaves_inside(dest_shapes, src_shapes, weave_superset, context):
    # context needed for colors
    new_weaves = []
    for we in weave_superset:
        [s1, s2] = [ hg.s for hg in we.hangpoints]
        try: i1, i2 = src_shapes.index(s1), src_shapes.index(s2)
        except: continue
        #
        new = we.copy()
        new.hangpoints[0].s, new.hangpoints[1].s = dest_shapes[i1], dest_shapes[i2]
        if context:
            create_weave(context, new, context.weave_colors[we])
        new_weaves.append( new )
    return new_weaves

def copy_weaves_into(dest_shapes, src_shapes, weave_superset, context):
    # context needed for colors
    new_weaves = []
    def find_list(l, item):
        try: return l.index(item)
        except: return -1
    for we in weave_superset:
        [s1, s2] = [ hg.s for hg in we.hangpoints]
        i1, i2 = find_list(src_shapes, s1), find_list(src_shapes, s2)
        if (i1, i2) == (-1, -1): continue
        #
        new = we.copy()
        if i1 >= 0: new.hangpoints[0].s = dest_shapes[i1]
        if i2 >= 0: new.hangpoints[1].s = dest_shapes[i2]
        if context:
            create_weave(context, new, context.weave_colors[we])
        new_weaves.append( new )
    return new_weaves

def move_selection_hook(hook, context, want_copy = False):
    setup_hook(hook, {pg.MOUSEMOTION, pg.MOUSEBUTTONDOWN}, (reset_hints, context))
    cx = context
    start_pos, _ = snappy_get_point(cx, pg.mouse.get_pos()) # want snappy? (i think yes but unsure)
    steal_menu_keys(hook, cx.menu, 'QWRASDF', {}) # Just to suppress, keep E = Unweave only
    #
    def inner(ev):
        if (ev.type == pg.KEYDOWN): return
        pos, _ = snappy_get_point(cx, ev.pos);
        match mouse_subtype(ev):
            case ms.RCLICK:
                hook.finish()
            case ms.LCLICK:
                if want_copy:
                    new_shapes = [ sh.moved(pos - start_pos) for sh in cx.selected ]
                    new_weaves = copy_weaves_inside( new_shapes, cx.selected, cx.weaves, cx)
                    #
                    cx.shapes, cx.selected = merge_into(cx.shapes, new_shapes, new_weaves)
                else:
                    for sh in cx.selected:
                        sh.move(pos - start_pos)
                    cx.shapes, cx.selected = merge_into(cx.shapes, cx.selected, cx.weaves)
                redraw_weaves(cx)
                hook.finish()
            case ms.MOTION:
                cx.hints = [ sh.moved(pos - start_pos) for sh in cx.selected ]
    #
    hook.event_loop(inner)

def transform_selection_hook(hook, context, want_copy = False):
    mirror_matrix = np.array([ [-1, 0], [0, 1] ])
    #
    cx = context
    setup_hook( hook, {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, (reset_hints, cx) )
    steal_menu_keys(hook, cx.menu, 'QWERASDF', {'S': "+Rotation", 'D': "-Rotation", 'F': "Flip"})
    def transformed_selection(matrix, center):
        return [ sh.transformed(matrix, center) for sh in cx.selected ]
    #
    rot_angle = 0
    mirror = False
    set_hints(cx, *cx.selected)
    def inner(ev):
        center, _ = snappy_get_point(cx, pg.mouse.get_pos())
        nonlocal rot_angle
        nonlocal mirror
        if ev.type == pg.KEYDOWN:
            match alpha_scan(ev):
                case 'S': rot_angle += cx.default_rotation
                case 'D': rot_angle -= cx.default_rotation
                case 'F': mirror = not mirror
        matrix = rot_matrix(rot_angle)
        if mirror: matrix = matrix @ mirror_matrix
        match mouse_subtype(ev):
            case ms.RCLICK:
                hook.finish()
            case ms.LCLICK:
                if want_copy:
                    new_shapes = [ sh.transformed(matrix, center) for sh in cx.selected ]
                    new_weaves = copy_weaves_inside(
                            new_shapes, cx.selected, cx.weaves, cx)
                    cx.shapes, cx.selected = merge_into(cx.shapes, new_shapes, new_weaves)
                else:
                    for sh in cx.selected:
                        sh.transform(matrix, center);
                    cx.shapes, cx.selected = merge_into(cx.shapes, cx.selected, cx.weaves)
                redraw_weaves(cx);
                hook.finish()
        if hook.active():
            cx.hints = [ sh.transformed(matrix, center) for sh in cx.selected ]
    #
    hook.event_loop(inner)

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            cleanup = lambda context: reset_hints(context))
def interactive_transform_hook(hook, context):
    hflip = np.array( [ [ 1, 0 ], [0, -1]] )
    def rot(cos, sin): return np.array( [[cos, -sin], [sin, cos]] )
    #
    cx = context
    actions = { 
            ms.LCLICK: "apply change", ms.RCLICK: "put copy",
            'Q': "cancel change", 'W': "done", 'E': "scale/rotate", 'R': "recenter",
            'A': "scale",         'S': "move", 'D': "rotate"      , 'F': "flip",
            }
    stolen_keys = { k: v for k, v in actions.items() 
                    if (type(k) is str and k in 'QWERASDF') }
    steal_menu_keys(hook, cx.menu, 'QWERASDF', stolen_keys)
    def action(ev):
        if ev.type == pg.KEYDOWN: key = alpha_scan(ev)
        else: key = mouse_subtype(ev)
        #
        try: return actions[key]
        except KeyError: return key
    #
    if context.grid_on:
        center = context.grid.center
    else:
        center, _ = snappy_get_point(cx, pg.mouse.get_pos())
    pendingT = None
    #
    while True:
        ev = yield
        try: pos = _evpos(cx, ev)
        except AttributeError: pos, _ = snappy_get_point(cx, pg.mouse.get_pos())
        # "Basic" Actions
        match action(ev):
            case "done": return
            case "cancel change": pendingT = None
            case "recenter": center = pos
            case "apply change":
                if pendingT:
                    for sh in cx.selected:
                        pendingT(pos, sh, copy = False)
                    cx.shapes, cx.selected = merge_into(cx.shapes, cx.selected, cx.weaves)
                    redraw_weaves(cx)
                    pendingT = None
            case "put copy":
                if pendingT:
                    new_shapes = [pendingT(pos, sh, copy = True) for sh in cx.selected]
                    new_weaves = copy_weaves_inside(new_shapes, cx.selected, cx.weaves, cx)
                    cx.shapes, cx.selected = merge_into(cx.shapes, new_shapes, new_weaves)
                    redraw_weaves(cx)
                    pendingT = None
        ##
        def apply_matrix(f):
            nonlocal pendingT
            def wrapped(to, sh, copy = True):
                try: matrix = f(to)
                except ZeroDivisionError: matrix = np.identity(2)
                #
                if copy: return sh.transformed(matrix, center)
                else: sh.transform(matrix, center)
            pendingT = wrapped
        # Set current transformation (parametrized by current pos)
        match action(ev):
            case "move":
                start = pos
                def do_move(to, sh, copy = True):
                    if copy: return sh.moved(to - start)
                    else: sh.move(to - start)
                pendingT = do_move
            case "rotate":
                start = pos
                @apply_matrix
                def rot_matrix(to):
                    [c1, s1] = unit(start - center)
                    [c2, s2] = unit(to - center)
                    return rot(c1 * c2 + s1 * s2, s2 * c1 - s1 * c2)
            case "flip":
                start = pos
                @apply_matrix
                def flip_matrix(to):
                    v = unit(to - center) - unit(start - center)
                    try: 
                        [x, y] = unit(v)
                        [c, s] = y, -x
                    except ZeroDivisionError:
                        [c, s] = unit(to - center)
                    return rot(c ** 2 - s ** 2, 2 * c * s) @ hflip
            case "scale":
                start = pos
                @apply_matrix
                def scale_matrix(to):
                    rstart = dist(center, start)
                    if near_zero(rstart):
                        raise ZeroDivisionError
                    rend = dist(center, to)
                    return rend / rstart * np.identity(2)
            case "scale/rotate":
                start = pos
                @apply_matrix
                def similitude_matrix(to):
                    rstart = dist(center, start)
                    rend = dist(center, to)
                    if near_zero(rstart) or near_zero(rend):
                        raise ZeroDivisionError
                    #
                    [c1, s1] = (start - center) / rstart
                    [c2, s2] = (to - center) / rend
                    return rend / rstart * rot(c1 * c2 + s1 * s2, s2 * c1 - s1 * c2)
        # Set hints (show pending change)
        if pendingT: set_hints(cx, *[pendingT(pos, sh, copy = True) for sh in cx.selected])
        else: set_hints(cx, Point(pos))
    ###


# Miniter
def miniter_hook(hook, context, cmd = ''):
    setup_hook(hook, { pg.KEYDOWN }, (context.text.write_section, 'term', []) )
    def set_line(cmd):
        context.text.write_section('term', [ 'CMD: ' + cmd + '_'])
    set_line(cmd)
    state = Rec(cmd = cmd)
    #
    def inner(ev):
        match bool(ev.mod & pg.KMOD_CTRL), ev.key:
            case True, pg.K_u: 
                state.cmd = ''
            case True, pg.K_c: 
                hook.finish()
            case True, pg.K_w | pg.K_BACKSPACE: 
                state.cmd = ' '.join(state.cmd.split()[:-1])
            #
            case False, pg.K_BACKSPACE:
                state.cmd = state.cmd[:-1]
            case False, pg.K_RETURN:
                if state.cmd.strip() != '': 
                    exit_code = miniter_exec(state.cmd, context)
                    state.cmd = ''
                    if context.oneshot_commands and not exit_code: 
                        hook.finish()
                else: 
                    hook.finish()
            case False, _:
                state.cmd += ev.unicode
            #
        if hook.active():
            set_line(state.cmd)
    #
    hook.event_loop(inner)

## Grid
@loop_hook({pg.MOUSEWHEEL, pg.MOUSEBUTTONDOWN})
def grid_sparseness_hook(hook, ev, context):
    match mouse_subtype(ev):
        case ms.WHEEL:
            context.grid.smallest_grad += params.grid_sparseness_scroll_speed * ev.y
            context.grid.smallest_grad = clamp(10, context.grid.smallest_grad, 500)
        case ms.LCLICK | ms.RCLICK:
            hook.finish()

@iter_hook( {pg.MOUSEMOTION, pg.MOUSEBUTTONDOWN}, 
            filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
            cleanup = lambda context: reset_hints(context))
def grid_phase_hook(hook, context):
    grid = context.grid
    def loop(ev):
        if mouse_subtype(ev) == ms.MOTION:
            set_hints(context, Line(grid.center, _evpos(context, ev), ndivs = 1) )
        if mouse_subtype(ev) == ms.RCLICK:
            hook.finish()
    hook.event_loop(loop)
    #
    while True:
        ev = yield
        pos = _evpos(context, ev)
        if almost_equal(pos, grid.center):
            # maybe post error
            continue
        [x, y] = pos - grid.center
        grid.phase = atan2(y, x) % (2 * np.pi)
        return

@iter_hook( {pg.MOUSEMOTION, pg.MOUSEBUTTONDOWN}, 
            filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
            cleanup = lambda context: reset_hints(context))
def grid_recenter_hook(hook, context):
    grid = context.grid
    def loop(ev):
        if mouse_subtype(ev) == ms.MOTION:
            set_hints(context, Point(_evpos(context, ev)) )
        if mouse_subtype(ev) == ms.RCLICK:
            hook.finish()
    hook.event_loop(loop)
    #
    ev = yield
    grid.center = _evpos(context, ev)

