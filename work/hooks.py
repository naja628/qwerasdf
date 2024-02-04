import pygame as pg

import params
from shape import *
from view import View
from menu import Menu
from miniter import miniter_exec
from context import *
from util import expr
from merge import merge_into # TODO restructure module

######### EVENT AND DISPATCH ##########
class EvHook:
    def __init__(self, make_hook, *a, **ka):
        self.attached = []
        self.watched = set()
        self.cleanup = lambda : None
        self.filter = None
        make_hook(self, *a, **ka)
    #
    def event_loop(self, event_loop):
        self.ev_loop = event_loop
    #
    def call_once(self, ev):
        assert ev.type in self.watched
        #
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
        self.track_hook(hook)
        return hook
    #
    def all_watched(self):
        return self.callstacks.keys()
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

## Pygame event related utils

# TODO probably OS dependent
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
    if ev.type           == pg.MOUSEMOTION:                    return ms.MOTION
    if ev.type           == pg.MOUSEWHEEL:                     return ms.WHEEL
        
def alpha_scan(event):
    # hopefully the magic 4 isn't OS/Hardware dependent
    # pygame doesn't seem to provide constants for `scancode`s (only `key`s)
    # I seem to recall SDL did? so maybe I missed something
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
    hook.cleanup = lambda: expr(menu.restore_display(), break_recursion()) 

## HOOKS
def zoom_hook(hook, context, factor = params.zoom_factor):
    setup_hook(hook, {pg.MOUSEWHEEL})
    #
    def inner(ev):
        context.view.zoom(pg.mouse.get_pos(), factor ** ev.y)
        redraw_weaves(context)
    #
    hook.event_loop(inner)

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

def color_picker_hook(hook, context):
    cx = context
    def cleanup(): 
        cx.show_palette = save_show_palette
        cx.show_picker = False
        cx.palette[cx.color_key] = save_color
#     setup_hook(hook, {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION, pg.KEYDOWN }, (cleanup, ))
#     hook.filter = lambda ev: not (ev.type == pg.KEYDOWN and alpha_scan(ev) not in cx.palette)
    
    setup_hook(hook, {pg.MOUSEBUTTONDOWN, pg.MOUSEMOTION}, (cleanup, ))
    steal_menu_keys(hook, cx.menu, 'QWERASDF', {})
    #
    save_show_palette = cx.show_palette
    cx.show_palette = True
    cx.show_picker = True
    save_color = cx.palette[cx.color_key]
    #
    def inner(ev):
        nonlocal save_color
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

def move_selection_hook(hook, context, want_copy = False):
    setup_hook(hook, {pg.MOUSEMOTION, pg.MOUSEBUTTONDOWN}, (reset_hints, context))
    cx = context
    start_pos, _ = snappy_get_point(cx, pg.mouse.get_pos()) # want snappy? (i think yes but unsure)
    #
    def inner(ev):
        pos, _ = snappy_get_point(cx, ev.pos);
        match mouse_subtype(ev):
            case ms.RCLICK:
                hook.finish()
            case ms.LCLICK:
                if want_copy:
                    new_shapes = [ sh.moved(pos - start_pos) for sh in cx.selected ]
                    new_weaves = copy_weaves_inside(
                            new_shapes, cx.selected, cx.weaves, cx)
                    #
                    cx.shapes, cx.selected = merge_into(cx.shapes, new_shapes, cx.weaves)
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
    steal_menu_keys(hook, cx.menu, 'QWERASDF', {'S': "+Rotation", 'D': "-Rotation", 'F': "Mirror"})
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
                        #
                        cx.shapes, cx.selected = merge_into(cx.shapes, new_shapes, cx.weaves)
                    else:
                        for sh in cx.selected:
                            sh.transform(matrix, center);
                        redraw_weaves(cx);
                    hook.finish()
                case ms.MOTION:
                    cx.hints = [ sh.transformed(matrix, center) for sh in cx.selected ]
    #
    hook.event_loop(inner)

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

# Selection actions
def delete_selection(context):
    cx = context
    keep_weaves = []
    for we in cx.weaves:
        sh1, sh2 = (hg.s for hg in we.hangpoints)
        if sh1 not in cx.selected and sh2 not in cx.selected:
            keep_weaves.append(we)
        else:
            del cx.weave_colors[we]
    cx.weaves = keep_weaves
    redraw_weaves(cx)
    cx.shapes = [ sh for sh in cx.shapes if not sh in cx.selected ]
    cx.selected = []

def unweave_inside_selection(context):
    cx = context
    keep_weaves = []
    for we in cx.weaves:
        sh1, sh2 = (hg.s for hg in we.hangpoints)
        if sh1 not in cx.selected and sh2 not in cx.selected:
            keep_weaves.append(we)
    cx.weaves = keep_weaves
    redraw_weaves(cx)

