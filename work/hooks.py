import pygame as pg

import params
from shape import *
from view import View
from menu import Menu
from miniter import miniter_exec
from context import *
from util import expr, param_decorator, clamp
from merge import merge_into # TODO restructure module

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
        # strategy?
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

# TODO probably OS dependent (Works on windows and Linux so far so ?)
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
    # hopefully the magic 4 isn't OS/Hardware dependent
    # pygame doesn't seem to provide constants for `scancode`s (only `key`s)
    # I seem to recall SDL did? so maybe I missed something TODO
    if not 4 <= event.scancode < 4 + 26:
        return '' 
    return chr(ord('A') + event.scancode - 4)

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
    hook.filter = lambda ev: (ev.type != pg.KEYDOWN) or (alpha_scan(ev) in stolen)
    #
    menu.temporary_display(stolen, labels)
    break_recursion = hook.cleanup
    hook.cleanup = lambda: [menu.restore_display(), break_recursion and break_recursion()]

## HOOKS
# def zoom_hook(hook, context, factor = params.zoom_factor):
#     setup_hook(hook, {pg.MOUSEWHEEL})
#     #
#     def inner(ev):
#         context.view.zoom(pg.mouse.get_pos(), factor ** ev.y)
#         redraw_weaves(context)
#     #
#     hook.event_loop(inner)
# 

@loop_hook({pg.MOUSEWHEEL})
def zoom_hook(hook, ev, context, factor = params.zoom_factor):
    context.view.zoom(pg.mouse.get_pos(), factor ** ev.y)
    redraw_weaves(context)

def click_move_hook(hook, context):
    setup_hook(hook, {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION})
    #
    state = Rec(start = None, start_corner = None)
    def move_view(pos):
        view = context.view
        dx = -view.ptord(pos[0] - state.start[0])
        dy = +view.ptord(pos[1] - state.start[1])
        view.corner = state.start_corner + np.array([dx, dy])
        redraw_weaves(context)
    #
    def inner(ev):
        match mouse_subtype(ev), state.start:
            case ms.RCLICK, None:
                state.start = ev.pos
                state.start_corner = context.view.corner
            case ms.RCLICK, start:
                move_view(ev.pos)
                state.start = None
            case _, None: pass
            case _, start:
                move_view(ev.pos)
    #
    hook.event_loop(inner)

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

def change_view_hook(hook, context):
    setup_hook(hook, { pg.MOUSEBUTTONDOWN })
    hook.filter = lambda ev: mouse_subtype(ev) == ms.LCLICK
    hook.attach(context.dispatch.add_hook(zoom_hook, context))
    hook.attach(context.dispatch.add_hook(click_move_hook, context))
    #
    def inner(ev):
        if mouse_subtype(ev) == ms.LCLICK:
            hook.finish()
    hook.event_loop(inner)

@iter_hook({ pg.MOUSEBUTTONDOWN })
def change_view_hook(hook, context):
    hook.attach(context.dispatch.add_hook(zoom_hook, context))
    hook.attach(context.dispatch.add_hook(click_move_hook, context))
    # filter HAS TO be set up here because it's the general one, not the iter one
    hook.filter = lambda ev: mouse_subtype(ev) == ms.LCLICK
    #
    ev = yield # Terminate on first event (ie LCLICK = done)

# Create shapes
def create_points_hook(hook, context):
    setup_hook(hook, {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, (reset_hints, context) )
    #
    def inner(ev):
        cur_pos, _ = snappy_get_point(context, ev.pos)
        point = Point(cur_pos)
        match mouse_subtype(ev):
            case ms.MOTION:
                set_hints(context, point)
            case ms.LCLICK:
                create_shapes(context, point)
    #
    hook.event_loop(inner)

def _evpos(context, ev): return snappy_get_point(context, ev.pos)[0]

@loop_hook({pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, lambda context: reset_hints(context))
def create_points_hook(hook, ev, context):
    point = Point(_evpos(context, ev))
    match mouse_subtype(ev):
        case ms.MOTION: set_hints(context, point)
        case ms.LCLICK: create_shapes(context, point)

def create_lines_hook(hook, context):
    setup_hook(hook, {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, (reset_hints, context) )
    #
    state = Rec(start = None)
    def inner(ev):
        cur_pos, _ = snappy_get_point(context, ev.pos)
        match mouse_subtype(ev), state.start:
            case ms.LCLICK, None: 
                state.start = cur_pos
            case ms.LCLICK, start: 
                create_shapes(context, Line(start, cur_pos) )
                state.start = None; reset_hints(context) # reset
            case ms.MOTION, None:
                set_hints(context,  Point(cur_pos) )
            case ms.MOTION, start:
                set_hints(context,  Line(start, cur_pos) )
    #
    hook.event_loop(inner)

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
            cleanup = lambda context: reset_hints(context) )
def create_lines_hook(hook, context):
    while True:
        start = None
        hook.event_loop( lambda ev: set_hints(context, Point(_evpos(context, ev))) )
        #
        ev = yield
        start = _evpos(context, ev)
        hook.event_loop( lambda ev: set_hints(context, Line(start, _evpos(context, ev))) )
        #
        ev = yield
        create_shapes(context, Line(start, _evpos(context, ev)))
        reset_hints(context)

def create_circles_hook(hook, context):
    setup_hook(hook, { pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION }, (reset_hints, context) )
    #
    state = Rec(point1 = None, center_first = True)
    def inner(ev):
        def reset():
            reset_hints(context)
            state.point1 = None
        #
        cur_pos, _ = snappy_get_point(context, ev.pos)
        match mouse_subtype(ev), state.point1, state.center_first:
            case ms.LCLICK, None, _: 
                state.point1 = cur_pos
            case ms.LCLICK, center, True: 
                create_shapes(context, Point(center), Circle(center, cur_pos) )
                reset()
            case ms.LCLICK, perim, False: 
                create_shapes( context, Point(cur_pos), Circle(cur_pos, perim) )
                reset()
            case ms.MOTION, None, _: 
                set_hints(context, Point(cur_pos) )
            case ms.MOTION, center, True: 
                set_hints(context, Point(center), Circle(center, cur_pos) )
            case ms.MOTION, perim, False: 
                set_hints(context, Point(cur_pos), Circle(cur_pos, perim) )
            case ms.RCLICK, _, _: 
                state.center_first = not state.center_first
    #
    hook.event_loop(inner)

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
            cleanup = lambda context: reset_hints(context) )
def create_circles_hook(hook, context):
    def wcircle(p1, p2):
        if center_first: return Circle(p1, p2)
        else: return Circle(p2, p1)
    #
    def evloop(ev):
        nonlocal center_first
        if mouse_subtype(ev) == ms.RCLICK: 
            center_first = not center_first
        set_hints(context, wcircle(point1, _evpos(context, ev)))
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
                wcircle(point1, _evpos(context, ev) ),
                Point(point1 if center_first else _evpos(context, ev)))
        reset_hints(context)

## Weave
def create_weaves_hook(hook, context):
    # Utils:
    def point_at_hang(hg):
        return hg.s.get_div(hg.i)
    #
    def hang_on_shape(candidates, shape):
        for hg in candidates:
            if hg.s == shape: return hg
        else: return None
    #
    # Setup
    setup_hook(hook, { pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION }, (reset_hints, context))
    state = Rec(hangs = [], incrs = context.weavity, nloops = 0)
    def update_hints(cur_pos, candidates):
        hints = [ Point(point_at_hang(hg)) for hg in state.hangs ]
        if candidates:
            hints += [ Point(cur_pos) ]
        if len(state.hangs) > 1 and (hg := hang_on_shape(candidates, state.hangs[1].s)):
            we = Weave.CreateFrom3(state.hangs + [hg], state.incrs, state.nloops)
            hints.append(we)
            if context.weaveback:
                back_weave = Weave.BackWeave(we)
                if back_weave: hints.append(back_weave)
        set_hints(context, *hints)
    #
    # Subhooks:
    def prefilter(candidates):
        in_selected = [ cd for cd in candidates if cd.s in context.selected ]
        if len(in_selected) == 1: return in_selected
        else: return candidates
    #
    def disambiguate_hook(hook, candidates):
        # post_info ...
        setup_hook(hook, { pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION }, (reset_hints, context))
        reset_hints(context)
        #
        def inner(ev):
            cur_pos, under_cursor = snappy_get_point(context, ev.pos)
            shapes = [hg.s for hg in under_cursor]
            inter = [ hg for hg in candidates if hg.s in shapes ]
            match mouse_subtype(ev), inter:
                case ms.MOTION, [hg]:
                    set_hints(context, hg.s)
                case ms.MOTION, _:
                    reset_hints(context)
                case ms.LCLICK, [hg]:
                    update_hints(point_at_hang(hg), [])
                    #
                    iter_pass.disambiguated = hg
                    hook.finish()
                    next(state.iter)
        #
        hook.event_loop(inner)
    #
    def turn_around_hook(hook):
        # post_info ...
        setup_hook(hook, { pg.MOUSEBUTTONDOWN, pg.MOUSEWHEEL } )
        hook.filter = lambda ev: mouse_subtype(ev) in { ms.MCLICK, ms.WHEEL }
        def inner(ev):
            match mouse_subtype(ev):
                case ms.WHEEL:
                    state.nloops += ev.y
                case ms.MCLICK:
                    state.nloops = 0 if state.nloops != 0 else -1
        hook.event_loop(inner)
    # Iter: keeping track of where we are is way easier than matching the 
    # (complex) current state
    iter_pass = Rec()
    def set_hangs_iter():
        subhook = None
        for i in range(2): # get first 2 hangs
            while not (cdt := prefilter(iter_pass.candidates)) : yield
            if len(cdt) == 1: state.hangs.append(cdt[0])
            else: 
                hook.attach(context.dispatch.add_hook(disambiguate_hook, cdt)); yield
                state.hangs.append(iter_pass.disambiguated)
            if i == 1 and state.hangs[1].s.loopy: 
                subhook = context.dispatch.add_hook(turn_around_hook)
                hook.attach(subhook)
            yield
        #
        while not (last_hang := hang_on_shape(iter_pass.candidates, state.hangs[1].s)): # get last hang
            # post_error("no shape in common")
            yield
        # create weave
        state.hangs.append(last_hang)
        we = Weave.CreateFrom3(state.hangs, state.incrs, state.nloops)
        create_weave(context, we)
        if context.weaveback:
            back_weave = Weave.BackWeave(we)
            if back_weave: create_weave(context, back_weave)
        # reset
        if subhook: subhook.finish(); subhook = None
        reset_hints(context)
        state.hangs, state.incrs, state.nloops = [], context.weavity, 0
    #
    state.iter = set_hangs_iter()
    def inner(ev):
        cur_pos, candidates = snappy_get_point(context, ev.pos)
        if mouse_subtype(ev) == ms.LCLICK:
            iter_pass.candidates = candidates
            try: next(state.iter)
            except StopIteration:
                state.iter = set_hangs_iter()
                next(state.iter)
        elif mouse_subtype(ev) == ms.RCLICK:
            inc0, inc1 = state.incrs
            state.incrs = -inc0, inc1
        update_hints(cur_pos, candidates)
    #
    hook.event_loop(inner)


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
        if subloop: subloop(ev)
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
            match candidates, filter_cdt(candidates, cx.selected):
                case ([ hg ], _) | (_, [ hg ]): return hg
                case [], []: assert False
                case (cdt, []) | (_, cdt) :
                    post_error("several shapes match. LCLICK -> disambiguate", cx)
                    # highlight shape
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

def select_color_hook(hook, context):
    cx = context
    def cleanup(): cx.show_palette = save_show_palette
    setup_hook(hook, set(), (cleanup,) )
    steal_menu_keys(hook, cx.menu, 'QWERASDF', {})
    #
    save_show_palette = cx.show_palette
    context.show_palette = True
    #
    def inner(ev):
        context.color_key = alpha_scan(ev)
        hook.finish()
    hook.event_loop(inner)

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

def color_picker_hook(hook, context):
    cx = context
    def cleanup(): 
        cx.show_palette = save_show_palette
        cx.show_picker = False
        cx.palette[cx.color_key] = save_color
    setup_hook(hook, {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, (cleanup, ))
    steal_menu_keys(hook, cx.menu, 'QWERASDF', {})
    #
    save_show_palette = cx.show_palette
    cx.show_palette = True
    cx.show_picker = True
    save_color = cx.palette[cx.color_key]
    #
    def inner(ev):
        if ev.type == pg.KEYDOWN:
            cx.palette[cx.color_key] = save_color
            cx.color_key = alpha_scan(ev)
            save_color = cx.palette[cx.color_key]
        else:
            cur_color = cx.color_picker.at_pixel(ev.pos)
            match mouse_subtype(ev), cur_color:
                case ms.RCLICK, _:
                    hook.finish()
                case _, None: pass
                case ms.MOTION, color:
                    cx.palette[cx.color_key] = color
                case ms.LCLICK, color:
                    cx.palette[cx.color_key] = color
                    save_color = color
        redraw_weaves(cx)
    hook.event_loop(inner)

def _color_picker_setup(hook, context):
    save_show_palette = context.show_palette
    state = Rec(save_color = context.palette[context.color_key], lum = 0.7)
    #
    def cleanup(): 
        context.show_palette = save_show_palette
        context.show_picker = False
        context.palette[context.color_key] = state.save_color
    hook.cleanup = cleanup
    steal_menu_keys(hook, context.menu, 'QWERASDF', {})
    #
    context.show_palette = True
    context.show_picker = True
    return state
@loop_hook({pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION, pg.MOUSEWHEEL}, setup = _color_picker_setup)
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

## Transformations
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
    hook.watched = {pg.MOUSEMOTION, pg.MOUSEBUTTONDOWN}
    #
    def inner(ev):
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
                        sh.move(pos - start_pos);
                redraw_weaves(cx)
                hook.finish()
            case ms.MOTION:
                cx.hints = [ sh.moved(pos - start_pos) for sh in cx.selected ]
    #
    hook.event_loop(inner)

def transform_selection_hook(hook, context, want_copy = False):
    mirror_matrix = np.array([ [-1, 0], [0, 1] ])
    def rot_matrix(angle):
        return np.array([
            [np.cos(angle), -np.sin(angle)],
            [np.sin(angle),  np.cos(angle)]
            ])
    #
    cx = context
    setup_hook( hook, {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, (reset_hints, cx) )
    steal_menu_keys(hook, cx.menu, 'QWERASDF', {'S': "+Rotation", 'D': "-Rotation", 'F': "Flip"})
    def transformed_selection(matrix, center):
        return [ sh.transformed(matrix, center) for sh in cx.selected ]
    #
    rot_angle = 0
    mirror = False
    def inner(ev):
        center, _ = snappy_get_point(cx, pg.mouse.get_pos())
        nonlocal rot_angle
        nonlocal mirror
        if ev.type == pg.KEYDOWN:
            match alpha_scan(ev):
                case 'S': rot_angle += cx.default_rotation
                case 'D': rot_angle -= cx.default_rotation
                case 'F': mirror = not mirror
        else:
            pos, _ = snappy_get_point(cx, ev.pos)
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
                    redraw_weaves(cx);
                    hook.finish()
                case ms.MOTION:
                    cx.hints = [ sh.transformed(matrix, center) for sh in cx.selected ]
    #
    hook.event_loop(inner)

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            filter = lambda ev: mouse_subtype(ev) in {ms.LCLICK, pg.KEYDOWN},
            cleanup = lambda context: reset_hints(context))
def interactive_transform_hook(hook, context):
    # TODO extra hints (axis etc)
    hflip = np.array( [ [ 1, 0 ], [0, -1]] )
    def rot(cos, sin): return np.array( [[cos, -sin], [sin, cos]] )
    def unit(u): 
        d = dist(u, [0, 0])
        if near_zero(d): raise ZeroDivisionError
        return np.array(u) / dist(u, [0, 0])
    #
    cx = context
    def evloop(ev):
        nonlocal center
        if mouse_subtype(ev) == ms.RCLICK: center = _evpos(cx, ev)
        #
        reset_hints(cx)
        if pending != cx.selected: cx.hints = [*pending]
        if pendingT: cx.hints += [ pendingT(_evpos(cx, ev), sh) for sh in pending ]
        else: cx.hints.append( Point(_evpos(cx, ev)) )
    hook.event_loop(evloop)
    submenu = {  
            'Q': "put down", 'W': "put copy",           'R': "close",
            'A': "still",    'S': "rotate", 'D': "move", 'F': "flip", }
    steal_menu_keys(hook, cx.menu, 'QWERASDF', submenu)
    #
    center, _ = snappy_get_point(cx, pg.mouse.get_pos())
    pending, pendingT = cx.selected, None
    #
    def action(ev): 
        try: return submenu[alpha_scan(ev)]
        except: return ''
    while True:
        # q put down w       e        r finish     
        # a put copy s move  d rot    f flip 
        ev = yield
        match action(ev):
            case "close": return
            case "move":
                start, _ = snappy_get_point(cx, pg.mouse.get_pos())
                pendingT = lambda end, sh: sh.moved(end - start)
            case "flip":
                def do_flip(on_axis, sh):
                    try: 
                        [c, s] = unit(on_axis - center)
                        # cos 2t = cos t ^ 2 - sin t ^ 2 | sin 2t = 2.sin t.cos t
                        matrix = rot(c ** 2 - s ** 2, 2 * c * s) @ hflip
                    except ZeroDivisionError:
                        matrix = np.identity(2)
                    return sh.transformed(matrix, center)
                pendingT = do_flip
            case "rotate":
                start, _ = snappy_get_point(cx, pg.mouse.get_pos())
                if almost_equal(start, center):
                    post_error("can't start on center", context)
                    continue
                def do_rot(to, sh):
                    try: 
                        [c1, s1] = unit(start - center)
                        [c2, s2] = unit(to - center)
                        # sin b - a = sin b cos a - sin a cos b
                        # cos b - a = cos a cos b + sin a sin b
                        matrix = rot(c1 * c2 + s1 * s2, s2 * c1 - s1 * c2)
                    except ZeroDivisionError:
                        matrix = np.identity(2)
                    return sh.transformed(matrix, center)
                pendingT = do_rot
            case "still": 
                pendingT = None
            case _:
                if pendingT:
                    pos, _ = snappy_get_point(cx, pg.mouse.get_pos())
                    pending = [ pendingT(pos, sh) for sh in pending ]
                    pendingT = None
        match action(ev):
            case "put copy": 
                new_weaves = copy_weaves_inside(pending, cx.selected, cx.weaves, cx)
                cx.shapes, cx.selected = merge_into(cx.shapes, pending, new_weaves)
                pending = cx.selected
            case "put down": 
                new_weaves = copy_weaves_into(pending, cx.selected, cx.weaves, cx)
                delete_selection(cx)
                cx.shapes, cx.selected = merge_into(cx.shapes, pending, new_weaves)
                return
        evloop(Rec(type = pg.MOUSEMOTION, pos = pg.mouse.get_pos()))

#     # rclick * 2: catch + release center
#     # keys for: 
#     #   f: flip ( mouse controls axis, lclick to confirm )
#     #   d: rotate lclick catch + lclick release
#     #   move:
#     #   put down copy
#     #   put down and exit
#     #   cancel
#     # hints:
#     #   keep all Ts but one intermdiate result, subhooks set last T, apply to hints
#     #   last_T may be undefined
#     #   moving does its own thing / has its own hints
#     vflip = np.array([ [-1, 0], [0, 1] ])
#     def rot_matrix(angle):
#         return np.array([
#             [np.cos(angle), -np.sin(angle)],
#             [np.sin(angle),  np.cos(angle)]
#             ])
#     ##
#     transforms = [] # (matrix, center) pairs
#     def push_transform(matrix, center):
#         transforms.append( (matrix, center) )
#     center, _ = snappy_get_point(cx, pg.mouse.get_pos())
#     # subhook( set center )
#     def inner(ev):
#         if (ev.type == KEYDOWN):
#             match alpha_scan(ev):
#                 case 'f': #flip
#                     def flip_matrix(pos)
#                         v = (pos - center) / dist(pos, center)
#                         x, y = v[0], v[1]
#                         return np.array([ [y, x], [x, -y] ])
#                 case 'd': #rotate
#                     # attach get from
#                     # def rot_matrix(pos)
#                 case 's': # move
#                     # attach hook
#                 case 'q': # cancel
#                     hook.finish()
#                 case 'e': # put down
#         else:
#             match mouse_subtype(ev):
#                 case ms.MOTION: pass
#     #
# 
# def interactive_transform(hook, context):
#     cx = context
#     setup_hook(hook, { pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, (reset_hints, cx) )
#     steal_menu_keys(hook, cx.menu, 'QWERASDF', {}) # TODO labels
#     #
#     center, _ = snappy_get_point(cx, pg.mouse.get_pos())
#     current_shapes = cx.selected
#     loose_center = False
#     pending_matrix = None
#     def inner(ev):
#         nonlocal center
#         if ev.type == pg.KEYDOWN: 
#             match alpha_scan(ev):
#                 case 'F': # flip
#                     @sub_hook(
#                             hook, {pg.MOUSEBUTTONDOWN}, 
#                             filter = lambda ev: mouse_subtype(ev) in { ms.LCLICK, ms.MOTION }
#                             )
#                     def set_flip(subhook, ev):
#                         nonlocal pending_matrix
#                         if (mouse_subtype(ev) == ms.LCLICK): subhook.finish()
#                         else:
#                             pos, _ = snappy_get_point(cx, ev.pos)
#                             v = (pos - center) / dist(pos, center)
#                             x, y = v[0], v[1]
#                             pending_matrix = np.array[ [y, x], [x, -y] ]
#                 case 'D': # rotate
#                     @sub_hook(
#                             hook, {pg.MOUSEBUTTONDOWN}, 
#                             filter = lambda ev: mouse_subtype(ev) in { ms.LCLICK, ms.MOTION }
#                             )
#                     def set_flip(subhook, ev):
#                         nonlocal pending_matrix
#                         if (mouse_subtype(ev) == ms.LCLICK): subhook.finish()
#                         else:
#                             pos, _ = snappy_get_point(cx, ev.pos)
#                             v = (pos - center) / dist(pos, center)
#                             x, y = v[0], v[1]
#                             pending_matrix = np.array[ [y, x], [x, -y] ]
# 
#         else:
#             pos, _ = snappy_get_point(cx, ev.pos) 
#             match mouse_subtype(ev):
#                 case ms.MOTION: pass
#                 case ms.RCLICK:
#                     # attach hook
#         #
#         if pending_matrix:
# 
#             cx.hints = [sh.transformed(pending_matrix, center) for sh in current_shapes ]
# 
# 

## Miniter
def miniter_hook(hook, context, cmd = ''):
    setup_hook(hook, { pg.KEYDOWN }, (context.bottom_text.set_line, context.TERMLINE, '')  )
    def set_line(cmd):
        context.bottom_text.set_line(context.TERMLINE, 'miniter: ' + cmd + '_', params.term_color)
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
                    miniter_exec(state.cmd, context)
                    state.cmd = ''
                else: 
                    hook.finish()
            case False, _:
                state.cmd += ev.unicode
                if params.term_xx_close and state.cmd[-2:].lower() == 'xx': hook.finish()
            #
        if hook.active():
            set_line(state.cmd)
    #
    hook.event_loop(inner)

## Selection
def select_hook(hook, context):
    setup_hook(hook, { pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION }, (reset_hints, context))
    #
    def inner(ev):
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
    #
    hook.event_loop(inner)

