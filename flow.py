import os
from copy import copy
from pygame import *

from shape import *
from context import g
from util import dist, Rec
import params
import text
from text import post_error, MENULINE1, TERMLINE
from miniter import miniter_exec

def snappy_get_point(pos, context = g):
    c = context # shorter to write
    rrad = c.view.ptord(params.snap_radius)
    shortest = rrad + params.eps
    point = c.view.ptor(pos)
    candidates = []
    for s in c.shapes:
        for i, div in enumerate(s.divs):
            if (d := dist(div, c.view.ptor(pos))) < min(rrad, shortest):
                shortest = d
                point = div
            if dist(point, div) < params.eps:
                candidates.append(Rec(s = s, i = i))
    # filter candidates
    candidates = [ cd for cd in candidates 
            if dist(cd.s.divs[cd.i], point) < params.eps ]
    return point, candidates

######### EVENT AND DISPATCH ##########
class EvHook:
    def __init__(self, make_hook, *args, **kwargs):
        self.cleanup = lambda : None
        self.iter = make_hook(self, *args, **kwargs)
        assert hasattr(self, 'watched') # should be set-up by `make_hook`
        self.done = False
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

############ PYGAME EVENTS UTILS/DEFINES ############
MS_LEFT = 1
MS_MID = 2
MS_RIGHT = 3

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
#
def is_motion(event):
    return event.type == MOUSEMOTION

def alpha_scan(event):
    if event.scancode == 44:
        return ' '
    if not 4 <= event.scancode <= 29:
        return ''
    return chr(ord('A') + event.scancode - 4)

########### INTERACTIVE ACTIONS ###################
def create_shapes(*shapes, context = g):
    context.shapes.extend(shapes)
    if hasattr(context, 'selected'):
        context.selected = list(shapes)

def zoom_hook(hook, factor = params.zoom_factor, context = g):
    hook.watched = { MOUSEWHEEL }
    def iter():
        while e := hook.ev:
            context.view.zoom(mouse.get_pos(), factor ** e.y)
            yield
    return iter()

def draw_circles_hook(hook, context = g):
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    #
    def cleanup(): context.hints = []
    hook.cleanup = cleanup
    #
    def iter():
        def get_circle(center, pos):
            rpos, _ = snappy_get_point(pos, context)
            return Circle(center, rpos)
        #
        center = None
        create_point_at_center = False
        while e := hook.ev:
            if left_click(e):
                if center is None:
                    center, m = snappy_get_point(e.pos)
                    if not m:
                        create_point_at_center = True
                else:
                    create_shapes(get_circle(center, e.pos), context = context)
                    if create_point_at_center:
                        context.shapes.append(Point(center))
                        create_point_at_center = False
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
                    a, _ = snappy_get_point(e.pos, context)
                else:
                    create_shapes(get_line(a, e.pos), context = context)
                    context.hints = []
                    a = None
            elif e.type == MOUSEMOTION and a is not None:
                context.hints = [get_line(a, e.pos)]
            yield
    return iter()

def create_weave_hook(hook, context = g):
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    def iter():
        c, hangs = context, [None] * 3
        #
        def update_hints_hook(hook):
            hook.watched = { MOUSEMOTION }
            def iter():
                while (e := hook.ev):
                    c.hints = [ Point(h.s.divs[h.i]) for h in hangs if (h != None) ]
                    under_cursor, m = snappy_get_point(hook.ev.pos, c)
                    if m: c.hints.append(Point(under_cursor))
                    if hangs[1] != None and m and m[0].s == hangs[1].s:
                        hint_hangs = hangs[:2] + [m[0]]
                        # c.hints.append(Weave(hint_hangs, c.weave_incrs))
                        c.hints.append(Weave.CreateFrom3(hint_hangs, c.weave_incrs))
                    yield
            return iter()
        #
        def get_hang():
            if not left_click(hook.ev): return 
            #
            _, matches = snappy_get_point(hook.ev.pos, c)
            if not matches: 
                post_error("no shape under cursor", context = c)
                return
            # for now just assume first match (TODO)
            # return Rec(s = matches[0].s, i = matches[0].i)
            return matches[0]
        #####
        mo_hook = c.dispatch.add_hook(update_hints_hook)
        def cleanup(): mo_hook.finish(); c.hints = []
        hook.cleanup = cleanup
        # loopy shapes problems? 
        while True:
            def assign_item(seq, i, assignment): # `seq[i] := assignment` is illegal
                seq[i] = assignment
                return seq[i]
            #
            for i in range(2):
                while assign_item(hangs, i, get_hang()) is None: yield
                yield
            #
            while assign_item(hangs, 2, get_hang()) is None or hangs[2].s != hangs[1].s:
                if hangs[2] is not None:
                    post_error("must belong to same shape", context = c)
                yield
            #
            # new_weave = Weave(hangs, c.weave_incrs)
            new_weave = Weave.CreateFrom3(hangs, c.weave_incrs)
            if hasattr(c, 'color_key') and hasattr(c, 'palette'):
                new_weave.set_color(c.color_key, c.palette)
            c.weaves.append(new_weave)
            hangs, c.hints = [None] * 3, [] # reset
            yield
            continue
    return iter()

def choose_color_hook(hook, context = g):
    hook.watched = {KEYDOWN}
    save_show = context.show_palette
    def cleanup(): context.show_palette = save_show
    hook.cleanup = cleanup
    #
    context.show_palette = True
    def iter():
        if (ch := alpha_scan(hook.ev)) in context.palette:
            context.color_key = ch
        return
        assert False; yield
    return iter()

def select_hook(hook, context = g):
    # left-click -> select ONE, right-click -> toggle selected
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    def cleanup(): context.hints = []
    hook.cleanup = cleanup
    #
    def iter():
        def get_shapes():
            if not hasattr(hook.ev, 'pos'): 
                return None
            #
            _, matches = snappy_get_point(hook.ev.pos, context)
            if not matches: 
                return None
            else: 
                return [m.s for m in matches]
        #
        while (ev := hook.ev):
            if (sh := get_shapes()):
                if is_motion(ev):
                    context.hints = sh
                else:
                    context.hints = []
                #
                if left_click(ev):
                    context.selected = sh
                elif right_click(ev):
                    tmp = []
                    for s in sh:
                        if s in context.selected:
                            context.selected.remove(s)
                        else:
                            tmp.append(s)
                    context.selected.extend(tmp)
            else:
                if left_click(ev):
                    context.selected = []
                context.hints = []
            yield
    return iter()

#### Select Actions
def unweave1(shape, context = g):
    c = context
    def connected(weave, shape):
        return (weave.hangpoints[0].s == shape) or (weave.hangpoints[1].s == shape)
    c.weaves = [w for w in c.weaves if not connected(w, shape)]
#
def unweave_selection(context = g):
    for sh in context.selected:
        unweave1(sh, context)
#
def delete_selection(context = g):
    c = context
    unweave_selection(c)
    c.shapes = [sh for sh in c.shapes if not sh in c.selected]
    c.selected = []

# Transform
# transform, copy-transform, move, copy-move
#
# move: copy of selected follows cursor. lclick -> confirm, rclick -> cancel
# copy-move: like move but selection is not deleted
## note: for copy only weaves INSIDE are copied, 
# transform : center follows cursor, add menu-keys for default rot,  
# rot: scroll angle +/-= default_rot, center follows cursor

#def copy_weaves_inside(dest, src, weave_superset)
def move_selection_hook(hook, *, want_copy = False, context = g):
    hook.watched = {MOUSEBUTTONDOWN, MOUSEMOTION}
    cx = context
    def cleanup(): cx.hints = []
    hook.cleanup = cleanup
    start_pos, _ = snappy_get_point(mouse.get_pos(), cx) # want snappy? (i think yes but unsure)
    def moved_selection(motion): # RAM problems ?
        return [ sh.moved(motion) for sh in cx.selected ]
    #
    def iter():
        while (ev := hook.ev):
            if right_click(ev): # = Cancel
                return
            cur_pos, _ = snappy_get_point(ev.pos, cx)
            if is_motion(ev):
                cx.hints = moved_selection(cur_pos - start_pos)
            elif left_click(ev): # = Confirm
                if want_copy:
                    new_shapes = moved_selection(cur_pos - start_pos)
                    new_weaves = []
                    for we in cx.weaves:
                        [s1, s2] = [ hg.s for hg in we.hangpoints]
                        print(id(s1), id(s2), [id(sh) for sh in cx.selected])
                        try:
                            print(cx.selected.index(s1))
                            print(cx.selected.index(s2))
                        except:
                            print(' missing at least 1')
                        try: i1, i2 = cx.selected.index(s1), cx.selected.index(s2)
                        except: continue
                        #
                        print('hello')
                        nw = we.copy()
                        print(new_shapes, id(new_shapes[i1]))
                        nw.hangpoints[0].s, nw.hangpoints[1].s = new_shapes[i1], new_shapes[i2]
                        new_weaves.append(nw)
                    #
                    context.shapes.extend( new_shapes )
                    context.selected = new_shapes
                    context.weaves.extend(new_weaves)
                else:
                    for sh in context.selected: 
                        sh.move(cur_pos - start_pos)
                return
            yield
    return iter()
#
def copymove_selection_hook(hook, context = g):
    return move_selection_hook(hook, want_copy = True, context = context)

############ MINITER HOOK #######################à
def miniter_hook(hook, context = g):
    hook.watched = {KEYDOWN}
    c = context
    def cleanup():
        c.text_area.set_line(TERMLINE, '') 
    hook.cleanup = cleanup
    def set_line(cmd):
        c.text_area.set_line(TERMLINE, 'miniter: ' + cmd + '_', params.term_color)
    set_line('')
    #
    def iter():
        command = ''
        while True:
            while (ev := hook.ev):
                # handle C-c, C-u, UP, DOWN, RETURN specially
                if ev.mod & KMOD_CTRL:
                    if ev.key == K_c:
                        return
                    if ev.key == K_u:
                        command = ''
                elif ev.key == K_BACKSPACE or ev.key == K_DELETE:
                    command = command[:-1]
                elif ev.key == K_RETURN:
                    if (command == ''): # double Enter exits terminal
                        return
                    status = miniter_exec(command)
                    #if status == 0: # 0 = good
                    #    term_history.append(command)
                    break
                # ignore ctrl/alt modded keys + ascii control codes
                elif ev.mod & KMOD_CTRL == 0: 
                    if ev.unicode and 127 != ord(ev.unicode) >= 32:
                        command += ev.unicode
                set_line(command)
                yield
            command = ''
            set_line(command)
            yield
    return iter()

######################## MENU ########################
class Menu:
    class Shortuct:
        def __init__(self, path): self.path = path
        def get(self): return self.path
    def __init__(self, nested = {}, pinned = {}):
        self._path = ""
        self.root = nested
        self.pos = self.root # pos is always a dict
        #
        self.pinned = pinned
    #
    def _is_leaf(self, thing):
        return type(thing) is str
    #
    def go(self, key, navigate = True):
        if key in self.pinned:
            return self.pinned[key]
        elif key in self.pos:
            down = self.pos[key]
            if self._is_leaf(down):
                return down
            else:
                if navigate:
                    match type(down[1]):
                        case dict: self.pos = down[1]; self._path += key
                        case Menu.Shortuct: self.go_path(down[1].get())
                return down[0]
        else:
            return None
    #
    def __getitem__(self, key):
        return self.go(key, navigate = False)
    def peek(self, key): # just an alias
        return self[key]
    #
    def go_path(self, path):
        self.pos = self.root
        self._path = ""
        for (i, key) in enumerate(path):
            if self.go(key) == None:
                self._path = path[:i]
                break
    #
    def path(self):
        return self._path
    #
    def up(self, n = 1): # 0 go to root
        self.go_path(self._path[:-n])
    #
    def show(self, context = g):
        menu_layout = ['QWER', 'ASDF', 'ZXCV']
        text_area = context.text_area
        #
        label_size = 12
        #
        for (i, row) in enumerate(menu_layout):
            line = "|"
            for key in row:
                label = self[key]
                #
                if label:
                    line += f" {key}: "
                    line += label[:label_size].ljust(label_size, ' ')
                else:
                    line += ' ' * (len(" X: ") + label_size)
                line += ' |'
            text_area.set_line(MENULINE1 + i, line)
    ###

_nested_menu = {
        'S': ("Selection", 
            { 'Q': "Unselect All", 'E': "Unweave", 'R': "Remove",
                'A': "Transform", 'S': "Cp-Transform", 'D': "Move", 'F': "Copy-Move"
                }),
        'D': ("New Shape", 
            {'A': "New Point", 'S': "New Segment", 'D': "New Circle", 'F' : ("Draw Weave", sho('F'))}),
        'F': ("Draw Weave", 
            {'A' : "Invert", 'S': "Select Color", 'D': ("New Shape", sho('D')), 'F': "Draw Weave"}),
        }
_pinned_menu = {'Z': "Menu Top", 'X': "Back", 'C': "Command"}
_menuaction_info = { # What the user has to do AFTER, not what it does
        "New Point": "lclick to add a point" #TODO
        "New Segment": "lclick on two points to draw a line between them"
        "New Circle": "lclick on the center and any point on the perimeter to draw a circle"
        "Draw Weave": "lclick on 3 points on (1 or) 2 shapes to add colorful strings"
        "Select Color": "press key to choose color"
        "Selection": "lclick -> select under cursor. rclick -> toggle selection"
        "Transform": "lclick -> confirm (shape will change), rclick -> cancel" # TODO
        "Cp-Transform": "lclick -> confirm (new copy will be created), rclick -> cancel" # TODO
        "Move": "lclick -> confirm (shape will move), rclick -> cancel"
        "Copy-Move": "lclick -> confirm (new copy will be created), rclick -> cancel"
        }

def menu_hook(hook, context = g):
    hook.watched = { KEYDOWN }
    c = context
    #
    sho = Menu.Shortcut
    #
    c.menu = Menu(_nested_menu, _pinned_menu)
    c.menu.show(c)
    def iter():
        cur_hook = None
        def set_hook(hook_fun, *a, **ka):
            if cur_hook: cur_hook.finish()
            if hook_fun: cur_hook = c.dispatch.add_hook(hook_fun, *a, *ka)
            else: top_hook = None
        #
        def detached_hook(hook_fun, *a, **ka): # does its thing / overrides controls
            return c.dispatch.add_hook(hook_fun, *a, **ka)
        def bound_hook(hook_fun, *a, **ka): # "killed" if main hook is reset
            tmp_hook = detached_hook(hook_fun, *a, **ka)
            if cur_hook: 
                oldcleanup = cur_hook.cleanup
                def cleanup(): tmp_hook.finish(); oldcleanup()
                cur_hook.cleanup = cleanup
            else: cur_hook = tmp_hook
        ###
        while (ev := hook.ev):
            key = alpha_scan(ev)
            if not key:
                yield; continue
            #
            print("got menu:", key) # debug
            menu_action = c.menu.go(key)
            if menu_action in {"Back", "Menu Top", "Command"}:
                match menu_action
                    # Pinned
                    case "Menu Top":
                        c.menu.go_path("")
                        set_top_hook(None)
                    case "Back":
                        set_top_hook(None) 
                        c.menu.up(1)
                    case "Command": detached_hook(miniter_hook, c)
                    case _: pass
            elif hasattr(cur_hook, 'forward_request') and cur_hook.forward_request(ev):
                ev.type = _ACCEPT_FORWARD
                event.post(ev)
            else:
                match menu_action:
                    # Create Shapes
                    case "New Point": pass # TODO
                    case "New Segment": set_hook(draw_lines_hook, c)
                    case "New Circle": set_hook(draw_circles_hook, c)
                    # Weave
                    case "Draw Weave": set_hook(create_weave_hook, c)
                    case "Invert":
                        inc0, inc1 = context.weave_incrs
                        context.weave_incrs = (-inc0, inc1)
                    case "Select Color": detached_hook(choose_color_hook, c)
                    # Selection
                    case "Selection": set_hook(select_hook, c)
                    case "Unselect All": context.selected = []
                    case "Unweave": unweave_selection(context = c)
                    case "Remove": delete_selection(context = c)
                    case "Transform": pass # TODO
                    case "Cp-Transform": pass # TODO
                    case "Move": bound_hook(move_selection_hook, context = c)
                    case "Copy-Move": bound_hook(copymove_selection_hook, context = c)
                    #
                    case _: pass
            c.menu.show(c)
            yield
    #
    return iter()
