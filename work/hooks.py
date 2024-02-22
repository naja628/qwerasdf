import pygame as pg

from params import params
from shape import *
from view import View
from menu import Menu
from miniter import miniter_exec
from context import *
from util import expr, param_decorator, clamp
from merge import merge_into # TODO restructure module
import save

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
    if not pg.KSCAN_A <= event.scancode < pg.KSCAN_A + 26:
        return '' 
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
        return (ev.type != pg.KEYDOWN) or ((key := alpha_scan(ev)) and key in stolen)
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
        hook.finsish()
    elif type == ms.WHEEL:
        context.autosaver.rewind(-ev.y)
    elif type == LOOP:
        load_me = context.autosaver.current_file()
        if load_me: load_to_context(context, load_me)
    elif type == ms.LCLICK or type == ms.RCLICK:
        hook.finish()

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

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            filter = lambda ev: mouse_subtype(ev) == ms.LCLICK,
            cleanup = lambda context: reset_hints(context) )
def create_arcs_hook(hook, context):
    cx, clockwise, subloop = context, False, None
    def loop(ev):
        nonlocal clockwise
        if mouse_subtype(ev) == ms.RCLICK:
            clockwise = not clockwise
        if subloop: subloop(ev)
    hook.event_loop(loop)
    #
    while True:
        subloop = lambda ev: set_hints(cx, Point(_evpos(cx, ev)))
        ev = yield
        center = _evpos(cx, ev)
        #
        subloop = lambda ev: set_hints(cx, Circle(center, _evpos(cx, ev)))
        ev = yield
        start = _evpos(cx, ev)
        #
        subloop = lambda ev: set_hints(cx, Arc(center, start, _evpos(cx, ev), clockwise = clockwise))
        ev = yield
        end = _evpos(cx, ev)
        #
        create_shapes(cx, Arc(center, start, end, clockwise = clockwise))

@iter_hook( {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, 
            cleanup = lambda context: reset_hints(context) )
def create_poly_hook(hook, context):
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
                    create_shapes(context, PolyLine(*points, loopy = True))
                    reset()
                else:
                    points.append(_evpos(context, ev))
            case ms.RCLICK:
                create_shapes(context, PolyLine(*points, loopy = False))
                reset()
            case _:
                set_hints(context, PolyLine(*points, pos, loopy = False))
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

## SELECTION
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
                    merge_into(cx.shapes, cx.selected, cx.weaves)
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
                        merge_into(cx.shapes, cx.selected, cx.weaves)
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
            'Q': "put down", 'W': "put copy", 'E': "still", 'R': "close",
            'A': "scale",    'S': "rotate", 'D': "move", 'F': "flip", }
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
                start, _ = snappy_get_point(cx, pg.mouse.get_pos())
#                 def do_flip(to, sh):
#                     try:
#                         xcenter = np.array([start[0], to[1]]) # ignore nonlocal center
#                         if near_zero(to[0] - start[0]):
#                             raise ZeroDivisionError
#                         ratio = (to[1] - start[1]) / (to[0] - start[0])
#                         matrix = np.array([
#                                 [0.0,  - 1 / ratio],
#                                 [- ratio, 0.0] ])
#                     except:
#                         matrix = np.identity(2)
#                     return sh.transformed(matrix, center)
                if almost_equal(start, center):
                    post_error("can't start on center", context)
                    continue
                def do_flip(to, sh):
                    try:
                        # prolly not the best way
                        [x, y] = unit(unit(to - center) - unit(start - center))
                        [c, s] = y, -x
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
            case "scale":
                start, _ = snappy_get_point(cx, pg.mouse.get_pos())
                if almost_equal(start, center):
                    post_error("can't start on center", context)
                    continue
                def do_scale(to, sh):
                    try:
                        rstart = dist(center, start)
                        rend = dist(center, to)
                        matrix = rend / rstart * np.identity(2)
                    except ZeroDivisionError:
                        return np.identity(2)
                    return sh.transformed(matrix, center)
                pendingT = scale
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

## MINITER
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

