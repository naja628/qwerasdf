from pygame import *

import params
from shape import *
from view import View
from menu import Menu

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
    def set_iter(self, ev_iter):
        self.iter = ev_iter
    #
    def call_once(self, ev):
        assert ev.type in self.watched
        #
        if hasattr(self, 'ev_loop'):
            self.ev_loop(ev)
        elif hasattr(self, 'iter'):
            self.ev = ev
            try: next(self.iter)
            except StopIteration: self.finish()
        else: assert False
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
        #return self.track_hook( EvHook(make_hook, *a, **ka) )
        # debug:
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

## CONTEXT
def snappy_get_point(context, pos):
    cx = context # shorter to write
    rrad = cx.view.ptord(params.snap_radius)
    shortest = rrad + params.eps
    point = cx.view.ptor(pos)
    candidates = []
    for s in cx.shapes:
        for i, div in enumerate(s.divs):
            if (d := dist(div, cx.view.ptor(pos))) < min(rrad, shortest):
                shortest = d
                point = div
            if dist(point, div) < params.eps:
                candidates.append(Rec(s = s, i = i))
    # filter candidates
    candidates = [ cd for cd in candidates 
            if dist(cd.s.divs[cd.i], point) < params.eps ]
    return point, candidates

# for performance maybe try something more numpy-y, like:
#def snappy_get_point(context, pos):
#    cx = context
#    sq_rrad = cx.view.ptord(params.snap_radius) ** 2
#    point = cx.view.ptor(pos)
#    shortest = sq_rrad + params.eps
#    for sh in cx.shapes:
#        rels = sh.divs - point
#        rels **= 2
#        [xs, ys] = np.split(rels, 2, axis = 1)
#        sqdists = xs + ys
#        i = np.argmin(sqdists)
#        if sqdists[i] < min(rrad, shortest):
#            point, shortest = sh.divs[i], sqdists[i]
#        if sqdists[i] < params.eps ** 2:
#            candidates.append(Rec(s = sh, i = i))
#    #filter candidates, they need to be equal to actual found
#    candidates = [ cd for cd in candidates 
#            if sqdist(cd.s.divs[cd.i], point) < params.eps ** 2]
#    return point, candidates

def create_weave(context, weave):
    context.pending_weaves.append( (context.color_key, weave) )
#
def redraw_weaves(context):
    context.redraw_weaves = True
#

# TODO move to context, implemented automerge logic
def create_shapes(context, *shapes):
    context.shapes.extend(shapes)
    context.selected = list(shapes)
    # TODO automerge

def set_hints(context, *hints):
    context.hints = list(hints)

def reset_hints(context):
    context.hints = []

## Pygame event related utils

# TODO probably OS dependent
MS_LEFT, MS_MID, MS_RIGHT = 1, 2, 3

ms = Rec()
ms.LCLICK, ms.MCLICK, ms.RCLICK, ms.LUNCLICK, ms.MUNCLICK, ms.RUNCLICK, ms.MOTION, ms.WHEEL = range(8)
def mouse_subtype(ev):
    button = getattr(ev, 'button', None)
    if (ev.type, button) == (MOUSEBUTTONDOWN, MS_LEFT):  return ms.LCLICK
    if (ev.type, button) == (MOUSEBUTTONDOWN, MS_MID):   return ms.MCLICK
    if (ev.type, button) == (MOUSEBUTTONDOWN, MS_RIGHT): return ms.RCLICK
    if (ev.type, button) == (MOUSEBUTTONUP, MS_LEFT):    return ms.LUNCLICK
    if (ev.type, button) == (MOUSEBUTTONUP, MS_MID):     return ms.MUNCLICK
    if (ev.type, button) == (MOUSEBUTTONUP, MS_RIGHT):   return ms.RUNCLICK
    if ev.type           == MOUSEMOTION:                 return ms.MOTION
    if ev.type           == MOUSEWHEEL:                  return ms.WHEEL
        
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

## HOOKS
def zoom_hook(hook, context, factor = params.zoom_factor):
    setup_hook(hook, {MOUSEWHEEL})
    #
    def inner(ev):
        context.view.zoom(mouse.get_pos(), factor ** ev.y)
        redraw_weaves(context)
    #
    hook.event_loop(inner)

# Create shapes
def create_points_hook(hook, context):
    setup_hook(hook, {MOUSEBUTTONDOWN, MOUSEMOTION}, (reset_hints, context) )
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
    setup_hook(hook, {MOUSEBUTTONDOWN, MOUSEMOTION}, (reset_hints, context) )
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
    setup_hook(hook, { MOUSEBUTTONDOWN, MOUSEMOTION }, (reset_hints, context) )
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
    setup_hook(hook, { MOUSEBUTTONDOWN, MOUSEMOTION }, (reset_hints, context))
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
        setup_hook(hook, { MOUSEBUTTONDOWN, MOUSEMOTION }, (reset_hints, context))
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
        setup_hook(hook, { MOUSEBUTTONDOWN, MOUSEWHEEL } )
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

# def create_weaves_hook(hook, context):
#     setup_hook(hook, { MOUSEBUTTONDOWN }, (reset_hints, context))
#     #
#     def point_at_hang(hg):
#         return hg.s.get_div(hg.i)
#     #
#     def hang_on_shape(candidates, shape):
#         for hg in candidates:
#             if hg.s == shape: return hg
#         else: return None
#     #
#     state = Rec(hangs = [], incrs = context.weavity, nloops = 0)
#     def update_hints_hook(hook):
#         setup_hook( hook, { MOUSEMOTION } )
#         def inner(ev):
#             cur_pos, candidates = snappy_get_point(context, ev.pos)
#             hints = [ Point(point_at_hang(hg)) for hg in state.hangs ]
#             if candidates:
#                 hints += [ Point(cur_pos) ]
#             if len(state.hangs) > 1 and (hg := hang_on_shape(candidates, state.hangs[1].s)):
#                 we = Weave.CreateFrom3(state.hangs + [hg], state.incrs, state.nloops)
#                 hints.append(we)
#                 #if context.weaveback: hints.append(Weave.back_weave(we))
#             set_hints(context, *hints)
#         #
#         hook.event_loop(inner)
#     #
#     def prefilter(candidates):
#         in_selected = [ cd for cd in candidates if cd.s in context.selected ]
#         if len(in_selected) == 1: return in_selected
#         else: return candidates
#     #
#     hook.attach(context.dispatch.add_hook(update_hints_hook))
#     hook.filter = (lambda ev: mouse_subtype(ev) == ms.LCLICK)
#     def iter():
#         cur_pos, candidates = snappy_get_point(context, hook.ev.pos)
#         while True: # we want to draw several weaves at once (until canceled)
#             for _ in range(2): # get 2 first hangs
#                 while True:
#                     cur_pos, candidates = snappy_get_point(context, hook.ev.pos)
#                     if not (candidates := prefilter(candidates)): yield; continue
#                     else: break
#                 if len(candidates) == 1: # one match, so it's what we want
#                     state.hangs.append(candidates[0])
#                     yield
#                 else: pass # for now. then delegate `disambiguate_hook`
#             #
#             while True: # get 3rd hang
#                 cur_pos, candidates = snappy_get_point(context, hook.ev.pos)
#                 if not (last_hang := hang_on_shape(candidates, state.hangs[1].s)):
#                     #post_error("no shape in common")
#                     yield; continue
#                 else: break
#             state.hangs.append(last_hang)
#             we = Weave.CreateFrom3(state.hangs, state.incrs, state.nloops)
#             create_weave(context, we)
#             #if context.weaveback: create_weave(context, Weave.back_weave(we))
#             # Reset
#             reset_hints(context)
#             state.hangs, state.incrs, state.nloops = [], context.weavity, 0
#     #
#     hook.set_iter( iter() )

# def create_weaves_hook(hook, context):
#     setup_hook(hook, { MOUSEBUTTONDOWN , MOUSEMOTION}, (reset_hints, context))
#     # TODO delegate hook for setting nloops with mousewheel
#     #
#     def point_at_hang(hg):
#         return hg.s.get_div[hg.i]
#     #
#     def hang_on_shape(candidates, shape):
#         for hg in candidates:
#             if hg.s == shape:
#                 return hg
#         else: return None
#     #
#     def try_get_hang(candidates):
#         if len(candidates) == 1:
#             return candidates[0]
#         if len( (sel_cdt := [hg for hg in candidates if hg.s in context.selected] )) == 1:
#             return sel_cdt[0]
#         return None
#     #
#     def disambiguate_hang_hook(hook, candidates):
#         #...
#     state = Rec(hangs = [], incrs = context.weavity, nloops = 0)
#     itarg = Rec(cdt = []) # for "arg-passing" (of a sort)
#     def next_hang_iter():
#         while len(state.hangs) < 2:
#             if (hg := try_get_hang(itarg.cdt)):
#                 state.hangs.append(hg)
#             else:
#                 subhook = context.dispatch(disambiguate_hang_hook, itstate.candidates)
#                 hook.delegate(subhook); yield # TODO need to stop inner
#                 state.hangs.append(subhook.result)
#             yield
#         #
#         while not (last_hg := hang_on_shape(itarg.cdt, state.hangs[1].s)):
#             #post_error("Must belong to same shape")
#             yield
#         state.hangs.append(last_hg)
#         return Weave.CreateFrom3(state.hangs, state.incrs, state.nloops)
#     state.iter = next_hang_iter()
#     #
#     def inner(ev):
#         if ev.type == MOUSEWHEEL:
#             state.nloops += ev.y
#             return
#         #
#         cur_pos, candidates = snappy_get_point(context, ev.pos) # todo mousewheel has no pos
#         match mouse_subtype(ev):
#             case ms.MOTION: # show hints
#                 hints = []
#                 hints = [ Point(point_at_hang(hg)) for hg in hangs ]
#                 if len(state.hangs) < 2 and candidates: # show first 2 hangs
#                     hints += [ Point(cur_pos) ]
#                 elif len(state.hangs) == 2: # show weave that would be created
#                     if (hg := hang_on_shape(candidates, state.hangs[1].s)): # incompatible
#                         hints += Weave.CreateFrom3(state.hangs + [hg], state.incrs, state.nloops)
#                 set_hints(context, *hints)
#             case ms.RCLICK: # invert direction
#                 inc0, inc1 = state.incrs
#                 state.incrs = -inc0, inc1
#             case ms.LCLICK: # try to get the next hang
#                 if candidates:
#                     try: 
#                         itstate.cdt = candidates
#                         next(state.iter)
#                     except StopIteration as stop: # reset
#                         create_weave(context, stop.value)
#                         state.hangs, state.incrs, state.nloops = [], context.weavity, 0
#                         state.iter = next_hang_iter
#                 else:
#                     #post_error("No shape under cursor")
#                     pass
#     ######
#     hook.event_loop(inner)




_menu_layout = ['QWER', 'ASDF', 'ZXCV']
_nested_menu = {
        'D': ("Create Shapes",
            {'A': "New Point", 'S': "New Segment", 'D': "New Circle"}),
        'F': "Draw Weaves"
        }

_pinned_menu = { 'X': "Menu Top", 'C': "Command"}

def menu_hook(hook, context):
    setup_hook(hook, {KEYDOWN}) # no cleanup for no
    #
    menu = context.menu
    state = Rec(main_hook = None)
    def set_hook(hook_fun, *a, **ka):
        if state.main_hook:
            state.main_hook.finish()
        #
        if hook_fun:
            state.main_hook = context.dispatch.add_hook(hook_fun, *a, **ka)
        else:
            state.main_hook = None
    #
    def inner(ev):
        if ev.key == K_SPACE:
            menu.go_path("")
            set_hook(None)
        key = alpha_scan(ev)
        menu_item = menu.go(key)
        match menu_item:
            # Pinned
            case "Menu Top":
                menu.go_path("")
                set_hook(None)
            case "New Point": set_hook(create_points_hook, context)
            case "New Segment": set_hook(create_lines_hook, context)
            case "New Circle": set_hook(create_circles_hook, context)
            case "Draw Weaves": set_hook(create_weaves_hook, context)
    #
    hook.event_loop(inner)

## RUN
from text import TextArea
g = Rec()
#
init() # init pygame
#
g.dispatch = EvDispatch()
#
g.shapes = []
g.selected = []
g.hints = []
#
g.palette = params.start_palette
g.color_key = 'Q'
g.color_weave_pairs = []
g.pending_weaves = []
g.redraw_weaves = True
g.weavity = (1, 1)
g.weaveback = True
#
g.menu = Menu(_nested_menu, _pinned_menu, _menu_layout)
#
g.view = View()
g.screen = display.set_mode(params.start_dimensions)
display.set_caption('QWERASDF')
g.weave_layer = Surface( g.screen.get_size() )
#
g.menubox = TextArea(g.screen.get_size()[0], numlines = 3)

def main():
    g.dispatch.add_hook(zoom_hook, g)
    g.dispatch.add_hook(menu_hook, g)
    #
    clock = time.Clock()
    RUNNING = True
    while RUNNING:
        if event.get(QUIT):
            RUNNING = False
        evs = event.get()
        # TODO maybe do sever `event.get` calls: 
        # 1: things we don't care about, 2: MOUSEMOTION, keep only last, 3: send latter + rest to `dispatch`
        # point: avoid computing `snappy_get_point` for every intermediate MOUSEMOTION
        g.dispatch.dispatch(evs)
        g.weave_layer.lock()
        # draw weaves
        if g.redraw_weaves:
            g.weave_layer.fill(params.background)
            g.pending_weaves += g.color_weave_pairs
            g.color_weave_pairs = []
            g.redraw_weaves = False
        for pair in g.pending_weaves:
            ckey, we = pair
            we.draw(g.weave_layer, g.view, color = g.palette[ckey])
            g.color_weave_pairs.append( (ckey, we) )
        g.weave_layer.unlock()
        g.pending_weaves = []
        #g.screen.fill(params.background) # not needed?
        g.screen.blit(g.weave_layer, (0, 0))
        # draw everything else on top
        g.screen.lock()
        # for we in g.weaves: we.draw(g.screen, g.view)
        for sh in g.shapes: sh.draw(g.screen, g.view, params.shape_color)
        for sel in g.selected: sel.draw(g.screen, g.view, color = params.select_color)
        for hi in g.hints: hi.draw(g.screen, g.view, color = params.hint_color)
        g.screen.unlock()
        bottom_elements = [g.menu.render(g.menubox)]
        elt_y = g.screen.get_size()[1]
        for elt in reversed(bottom_elements):
            elt_y -= elt.get_size()[1]
            g.screen.blit(elt, (0, elt_y))
        #
        display.flip()
        clock.tick(60);
    quit() # from pygame

main()
exit()

######################## MENU ########################
# _sho = Menu.Shortcut
# _nested_menu = {
#         'S': ("Selection", 
#             { 'Q': "Unselect All", 'E': "Unweave", 'R': "Remove",
#                 'A': "Transform", 'S': "Cp-Transform", 'D': "Move", 'F': "Copy-Move"
#                 }),
#         'D': ("New Shape", {
#             'W': "New Polyline",
#             'A': "New Point", 'S': "New Segment", 'D': "New Circle", 'F' : ("Draw Weave", _sho('F'))}),
#         'F': ("Draw Weave", {
#             'W' : "Color Picker",
#             'A' : "Invert", 'S': "Select Color", 'D': ("New Shape", _sho('D')), 'F': "Draw Weave"}),
#         }
# del _sho

# _menuaction_info = { # What the user has to do AFTER, not what it does
#         "Command": "Termin: 'ls': list of commands. Ctrl-C: close (or Enter on empty prompt, or XX)",
#         "New Point": "LCLICK to add a point", 
#         "New Segment": "LCLICK on two points to draw a line between them",
#         "New Polyline": "LCLICK: add point OR (on start) connect and finish | RCLICK: finish",
#         "New Circle": "LCLICK on the center and any point on the perimeter to draw a circle",
#         "Draw Weave": "LCLICK on 3 points on (1 or) 2 shapes to add colorful strings",
#         "Select Color": "press key (QWERASDF) to choose color",
#         "Selection": "LCLICK: select under cursor | RCLICK: toggle select-state under cursor",
#         "Transform": "LCLICK: confirm (shape will change) | RCLICK: cancel",
#         "Cp-Transform": "LCLICK: confirm (new copy will be created) | RCLICK: cancel",
#         "Move": "LCLICK: confirm (shape will move) | RCLICK: cancel",
#         "Copy-Move": "LCLICK: confirm (new copy will be created) | RCLICK: cancel",
#         "Color Picker": "LCLICK : apply | RCLICK : close | QWERASDF : change color | WHEEL: change brightness",
#         }
