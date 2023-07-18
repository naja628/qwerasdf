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
        make_hook(self, *a, **ka)
        assert hasattr(self, 'ev_loop')
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
                hooks[-1].call_once(ev) # Heart
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

# TODO move to context, implemented automerge logic
def create_shapes(context, *shapes):
    context.shapes.extend(shapes)
    context.selected = list(shapes)
    # TODO automerge

def set_hints(context, *hints):
    context.hints = list(hints)

def reset_hints(context):
    context.hints = []

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

## Pygame event related utils

MS_LEFT, MS_MID, MS_RIGHT = 1, 2, 3

ms = Rec()
ms.LCLICK, ms.MCLICK, ms.RCLICK, ms.LUNCLICK, ms.MUNCLICK, ms.RUNCLICK, ms.MOTION = range(7)
def mouse_subtype(ev):
    button = getattr(ev, 'button', None)
    if (ev.type, button) == (MOUSEBUTTONDOWN, MS_LEFT):  return ms.LCLICK
    if (ev.type, button) == (MOUSEBUTTONDOWN, MS_MID):   return ms.MCLICK
    if (ev.type, button) == (MOUSEBUTTONDOWN, MS_RIGHT): return ms.RCLICK
    if (ev.type, button) == (MOUSEBUTTONUP, MS_LEFT):    return ms.LUNCLICK
    if (ev.type, button) == (MOUSEBUTTONUP, MS_MID):     return ms.MUNCLICK
    if (ev.type, button) == (MOUSEBUTTONUP, MS_RIGHT):   return ms.RUNCLICK
    if ev.type           == MOUSEMOTION:                 return ms.MOTION
        
def alpha_scan(event):
    if event.scancode == 44:
        return ' '
    if not 4 <= event.scancode <= 29:
        return ''
    return chr(ord('A') + event.scancode - 4)

## HOOKS
def zoom_hook(hook, context, factor = params.zoom_factor):
    setup_hook(hook, {MOUSEWHEEL})
    #
    def inner(ev):
        context.view.zoom(mouse.get_pos(), factor ** ev.y)
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
                state.start = None # reset
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

_nested_menu = {
        'D': ("Create Shapes",
            {'A': "New Point", 'S': "New Line", 'D': "New Circle"})
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
                print("set hook to None")
            case "New Point": set_hook(create_points_hook, context)
            case "New Line": set_hook(create_lines_hook, context)
            case "New Circle": set_hook(create_circles_hook, context)
    #
    hook.event_loop(inner)

from text import TextArea
def main():
    g = Rec()
    #
    g.dispatch = EvDispatch()
    #
    g.shapes = []
    g.selected = []
    g.hints = []
    #
    g.menu = Menu(_nested_menu, _pinned_menu)
    #
    g.view = View()
    g.screen = display.set_mode(params.start_dimensions)
    display.set_caption('QWERASDF')
    #
    # g.textarea = TextArea() 
    #
    # hooks
    g.dispatch.add_hook(zoom_hook, g)
    g.dispatch.add_hook(menu_hook, g)
    #
    clock = time.Clock()
    RUNNING = True
    while RUNNING:
        if event.get(QUIT):
            RUNNING = False
        evs = event.get()
        g.dispatch.dispatch(evs)
        # draw weaves
        # TODO draw on surface first first then blit on screen
        # only redraw things when needed
        # DRAW
        g.screen.fill( (0,0,0) )
        g.screen.lock()
        # for we in g.weaves: we.draw(g.screen, g.view)
        for sh in g.shapes: sh.draw(g.screen, g.view)
        for sel in g.selected: sel.draw(g.screen, g.view, color = params.select_color)
        for hi in g.hints: hi.draw(g.screen, g.view, color = params.hint_color)
        g.screen.unlock()
        #
        display.flip()
        clock.tick(30);
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
