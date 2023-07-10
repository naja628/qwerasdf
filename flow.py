import os
from copy import copy
from pygame import *

from shape import *
from context import g
from util import dist, Rec, do_chain, clamp, eprint
import params
import text
from text import post_error, post_info, MENULINE1, TERMLINE
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
        self.attached = []
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
        for sub in self.attached:
            sub.finish()
        self.done = True
        self.watched = set()
        self.cleanup()
    #
    def attach(self, other):
        self.attached.append(other)
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
_ACCEPT_FORWARD = event.custom_type()

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

def click_move_hook(hook, context = g):
    hook.watched = {MOUSEBUTTONDOWN}
    view = context.view
    #
    def subhook(hook, start):
        hook.watched = {MOUSEMOTION, MOUSEBUTTONDOWN}
        post_info("CLICK again to release")
        start_corner = view.corner
        #
        def iter():
            while (ev := hook.ev):
                dx = -view.ptord(ev.pos[0] - start[0])
                dy = +view.ptord(ev.pos[1] - start[1])
                view.corner = start_corner + np.array([dx, dy])
                if right_click(ev) or left_click(ev): return
                else: yield
        return iter()
    #
    def iter():
        while (ev := hook.ev):
            if right_click(ev):
                context.dispatch.add_hook(subhook, ev.pos)
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
            elif e.type == MOUSEMOTION:
                if center is None:
                    context.hints = [ Point(snappy_get_point(e.pos, context)[0]) ]
                else:
                    context.hints = [get_circle(center, e.pos)]
            yield
    return iter()

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
            elif e.type == MOUSEMOTION:
                if a is None:
                    context.hints = [ Point(snappy_get_point(e.pos, context)[0]) ]
                else:
                    context.hints = [get_line(a, e.pos)]
            yield
    return iter()

def draw_points_hook(hook, context = g):
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    def cleanup(): context.hints = []
    hook.cleanup = cleanup
    #
    def iter():
        def get_point(pos):
            return Point( snappy_get_point(ev.pos, context)[0] )
        #
        while (ev := hook.ev):
            if left_click(ev):
                create_shapes(get_point(ev.pos), context = context)
            elif ev.type == MOUSEMOTION:
                context.hints = [ get_point(ev.pos) ]
            yield
    return iter()

def draw_poly_lines_hook(hook, context = g):
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    def cleanup(): context.hints = []
    hook.cleanup = cleanup
    #
    def iter():
        points = [None] # always including under cursor
        while (ev := hook.ev):
            pos, _ = snappy_get_point(ev.pos, context)
            if len(points) > 2 and context.view.rtopd( dist(pos, points[0]) ) < params.snap_radius:
                pos = points[0]
            points[-1] = pos
            context.hints = [PolyLine(*points, loopy = False)]
            if left_click(ev): 
                if len(points) >= 2 and near_zero( dist(pos, points[0]) ):
                    create_shapes(PolyLine(*points[:-1], loopy = True), context = context)
                    points, context.hints = [None], []; yield; continue
                points.append(None)
            elif len(points) >= 2 and right_click(ev):
                create_shapes(PolyLine(*points[:-1], loopy = False), context = context)
                points, context.hints = [None], []
            #
            yield
    return iter()

def create_weave_hook(hook, context = g):
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    disambiguate_index = 0
    #
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
            new_weave = Weave.CreateFrom3(hangs, c.weave_incrs)
            if hasattr(c, 'color_key') and hasattr(c, 'palette'):
                new_weave.set_color(c.color_key, c.palette)
            c.weaves.append(new_weave)
            hangs, c.hints = [None] * 3, [] # reset
            yield
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
            assert hasattr(hook.ev, 'pos')
            # if not hasattr(hook.ev, 'pos'): 
            #     return None
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
def unweave_pre_delete(context = g):
    for sh in context.selected:
        unweave1(sh, context)
#
def delete_selection(context = g):
    c = context
    unweave_pre_delete(c)
    c.shapes = [sh for sh in c.shapes if not sh in c.selected]
    c.selected = []
#
def unweave_inside_selection(context = g):
    cx = context
    new_weaves = []
    for we in cx.weaves:
        s1, s2 = (hg.s for hg in we.hangpoints)
        if not (s1 in cx.selected and s2 in cx.selected):
            new_weaves.append(we)
    cx.weaves = new_weaves

def copy_weaves_inside(dest_shapes, src_shapes, weave_superset):
    new_weaves = []
    for we in weave_superset:
        [s1, s2] = [ hg.s for hg in we.hangpoints]
        try: i1, i2 = src_shapes.index(s1), src_shapes.index(s2)
        except: continue
        #
        new = we.copy()
        new.hangpoints[0].s, new.hangpoints[1].s = dest_shapes[i1], dest_shapes[i2]
        new_weaves.append(new)
    return new_weaves

def move_selection_hook(hook, *, want_copy = False, context = g):
    hook.watched = {MOUSEBUTTONDOWN, MOUSEMOTION}
    cx = context
    def cleanup(): cx.hints = []
    hook.cleanup = cleanup
    start_pos, _ = snappy_get_point(mouse.get_pos(), cx) # want snappy? (i think yes but unsure)
    def moved_selection(motion):
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
                    new_weaves = copy_weaves_inside(new_shapes, cx.selected, cx.weaves)
                    #
                    cx.shapes.extend(new_shapes)
                    cx.weaves.extend(new_weaves)
                    cx.selected = new_shapes
                else:
                    for sh in context.selected: 
                        sh.move(cur_pos - start_pos)
                return
            yield
    return iter()
#
def copymove_selection_hook(hook, context = g):
    return move_selection_hook(hook, want_copy = True, context = context)

def transform_selection_hook(hook, *, want_copy = False, context = g):
    mirror_matrix = np.array([ [-1, 0], [0, 1] ])
    def rot_matrix(angle):
        return np.array([
            [np.cos(angle), -np.sin(angle)],
            [np.sin(angle),  np.cos(angle)]
            ])
    ##
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION, _ACCEPT_FORWARD}
    cx = context
    cx.menu.temporary_display('QWERASDF', {'S': "+Rotaion", 'D': "-Rotation", 'F': "Mirror"})
    def cleanup(): cx.hints = []; cx.menu.restore_display() 
    hook.cleanup = cleanup
    hook.forward_request = (lambda ev: ev.type == KEYDOWN and alpha_scan(ev) in 'ASDFQWER')
    def transformed_selection(matrix, center):
        return [ sh.transformed(matrix, center) for sh in cx.selected ]
    #
    def iter():
        rot_angle = 0
        mirror = False
        while (ev := hook.ev):
            if right_click(ev): # = Cancel
                return
            #
            if (ev.type == _ACCEPT_FORWARD):
                match alpha_scan(ev):
                    case 'A': pass # TODO (add new hook)
                    case 'S': rot_angle += cx.default_rotation
                    case 'D': rot_angle -= cx.default_rotation
                    case 'F': mirror = not mirror
                yield
            #
            matrix = rot_matrix(rot_angle)
            if mirror: matrix = matrix @ mirror_matrix
            center, _ = snappy_get_point(mouse.get_pos(), cx)
            #
            if is_motion(ev):
                cx.hints = transformed_selection(matrix, center)
            elif left_click(ev): # = Confirm
                if want_copy:
                    new_shapes = transformed_selection(matrix, center)
                    new_weaves = copy_weaves_inside(new_shapes, cx.selected, cx.weaves)
                    #
                    cx.shapes.extend(new_shapes)
                    cx.weaves.extend(new_weaves)
                    cx.selected = new_shapes
                else:
                    for sh in context.selected: 
                        sh.transform(matrix, center)
                return
            yield
    return iter()
#
def copytransform_selection_hook(hook, context = g):
    return transform_selection_hook(hook, want_copy = True, context = context)

############ MINITER HOOK #######################
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
                    if (command.strip() == ''): # double Enter exits terminal
                        return
                    status = miniter_exec(command)
                    break
                # ignore ctrl/alt modded keys + ascii control codes
                elif ev.mod & KMOD_CTRL == 0: 
                    if ev.unicode and 127 != ord(ev.unicode) >= 32:
                        command += ev.unicode
                        if params.term_xx_close and command[-2:].lower() == 'xx': return
                set_line(command)
                yield
            command = ''
            set_line(command)
            yield
    return iter()

######################## MENU ########################
class Menu:
    class Shortcut:
        def __init__(self, path): self.path = path
        def get(self): return self.path
    ###
    def __init__(self, nested = {}, pinned = {}):
        self._path = ""
        self.root = nested
        self.pos = self.root # pos is always a dict
        #
        self.pinned = pinned
        self.temp_show = {}
        self.temp_show_mask = ''
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
                    if type(down[1]) is dict: self.pos = down[1]; self._path += key
                    elif type(down[1]) is Menu.Shortcut: self.go_path(down[1].get())
                    else: assert False
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
    def temporary_display(self, mask, items):
        self.temp_show_mask = mask
        self.temp_show = items
    #
    def restore_display(self):
        self.temporary_display('', {})
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
                if key in self.temp_show_mask:
                    if key in self.temp_show: label = self.temp_show[key]
                    else: label = None
                else:
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

_sho = Menu.Shortcut
_nested_menu = {
        'S': ("Selection", 
            { 'Q': "Unselect All", 'E': "Unweave", 'R': "Remove",
                'A': "Transform", 'S': "Cp-Transform", 'D': "Move", 'F': "Copy-Move"
                }),
        'D': ("New Shape", {
            'W': "New Polyline",
            'A': "New Point", 'S': "New Segment", 'D': "New Circle", 'F' : ("Draw Weave", _sho('F'))}),
        'F': ("Draw Weave", {
            'W' : "Color Picker",
            'A' : "Invert", 'S': "Select Color", 'D': ("New Shape", _sho('D')), 'F': "Draw Weave"}),
        }
del _sho
_pinned_menu = {'Z': "Menu Top", 'X': "Back", 'C': "Command"}
_menuaction_info = { # What the user has to do AFTER, not what it does
        "Command": "Termin: 'ls': list of commands. Ctrl-C: close (or Enter on empty prompt, or XX)",
        "New Point": "LCLICK to add a point", 
        "New Segment": "LCLICK on two points to draw a line between them",
        "New Polyline": "LCLICK: add point OR (on start) connect and finish | RCLICK: finish",
        "New Circle": "LCLICK on the center and any point on the perimeter to draw a circle",
        "Draw Weave": "LCLICK on 3 points on (1 or) 2 shapes to add colorful strings",
        "Select Color": "press key (QWERASDF) to choose color",
        "Selection": "LCLICK: select under cursor | RCLICK: toggle select-state under cursor",
        "Transform": "LCLICK: confirm (shape will change) | RCLICK: cancel",
        "Cp-Transform": "LCLICK: confirm (new copy will be created) | RCLICK: cancel",
        "Move": "LCLICK: confirm (shape will move) | RCLICK: cancel",
        "Copy-Move": "LCLICK: confirm (new copy will be created) | RCLICK: cancel",
        "Color Picker": "LCLICK : apply | RCLICK : close | QWERASDF : change color | WHEEL: change brightness",
        }

def menu_hook(hook, context = g):
    hook.watched = { KEYDOWN }
    c = context
    #
    c.menu = Menu(_nested_menu, _pinned_menu)
    c.menu.show(c)
    def iter():
        main_hook = None
        forward_request = None
        def set_hook(hook_fun, *a, **ka):
            nonlocal main_hook, forward_request
            if main_hook: main_hook.finish(); forward_request = None
            #
            if hook_fun:
                main_hook = c.dispatch.add_hook(hook_fun, *a, *ka)
                forward_request = getattr(main_hook, 'forward_request', None)
            else: main_hook = None
        #
        def detached_hook(hook_fun, *a, **ka): # does its thing / overrides controls
            return c.dispatch.add_hook(hook_fun, *a, **ka)
        def bound_hook(hook_fun, *a, **ka): # "killed" if main hook is reset
            # this seemED like a good a way to do it but it's clearly not the way
            # eh it works for now
            def unset_request():
                nonlocal forward_request
                forward_request = None
            #
            nonlocal main_hook, forward_request
            tmp_hook = detached_hook(hook_fun, *a, **ka)
            if hasattr(tmp_hook, 'forward_request'):
                forward_request = tmp_hook.forward_request
                tmp_hook.cleanup = do_chain(unset_request, tmp_hook.cleanup)
            #
            if main_hook: main_hook.attach(tmp_hook)
            else: main_hook = tmp_hook
        ###
        while (ev := hook.ev):
            key = alpha_scan(ev)
            if not key:
                yield; continue
            #
            #eprint("got menu:", key) # debug
            if main_hook and main_hook.done: forward_request = None
            menu_action = c.menu.go(key)
            if menu_action in {"Back", "Menu Top", "Command"}:
                try: post_info(_menuaction_info[menu_action])
                except KeyError: pass
                match menu_action:
                    # Pinned
                    case "Menu Top":
                        c.menu.go_path("")
                        set_hook(None)
                    case "Back":
                        set_hook(None) 
                        c.menu.up(1)
                    case "Command": detached_hook(miniter_hook, c)
            elif forward_request and forward_request(ev):
                #eprint('forward')
                ev_dict = ev.__dict__
                event.post(event.Event(_ACCEPT_FORWARD, **ev_dict))
            else:
                #eprint('no forward')
                try: post_info(_menuaction_info[menu_action])
                except KeyError: pass
                match menu_action:
                    # Create Shapes
                    case "New Point": set_hook(draw_points_hook, c)
                    case "New Segment": set_hook(draw_lines_hook, c)
                    case "New Polyline": set_hook(draw_poly_lines_hook, c)
                    case "New Circle": set_hook(draw_circles_hook, c)
                    # Weave
                    case "Draw Weave": set_hook(create_weave_hook, c)
                    case "Invert":
                        inc0, inc1 = context.weave_incrs
                        context.weave_incrs = (-inc0, inc1)
                    case "Select Color": detached_hook(choose_color_hook, c)
                    case "Color Picker": set_hook(color_picker_hook, c)
                    # Selection
                    case "Selection": set_hook(select_hook, c)
                    case "Unselect All": context.selected = []
                    case "Unweave": unweave_inside_selection(context = c)
                    case "Remove": delete_selection(context = c)
                    case "Transform": bound_hook(transform_selection_hook, context = c)
                    case "Cp-Transform": bound_hook(copytransform_selection_hook, context = c)
                    case "Move": bound_hook(move_selection_hook, context = c)
                    case "Copy-Move": bound_hook(copymove_selection_hook, context = c)
                    #
                    case _: pass
            yield
    #
    return iter()

def color_picker_hook(hook, context = g):
    # lclick apply, rclick exit, qwerasdf change color, mousewheel change brightness
    # params -> color_picker_scroll_speed
    hook.watched = { MOUSEWHEEL, MOUSEMOTION, MOUSEBUTTONDOWN, _ACCEPT_FORWARD }
    hook.forward_request = lambda ev: (ev.type == KEYDOWN and alpha_scan(ev) in 'QWERASDF')
    #
    cx = context
    color_picker, palette = cx.color_picker, cx.palette
    save_color_key, save_show_palette = cx.color_key, cx.show_palette
    cx.show_color_picker, cx.show_palette = True, True
    def tmp_cleanup(): cx.show_color_picker = False; cx.show_palette = save_show_palette
    hook.cleanup = tmp_cleanup
    #
    def iter():
        def cleanup():
            cx.show_color_picker = False
            cx.color_key, cx.show_palette = save_color_key, save_show_palette
            if color_key and save_color:
                palette[color_key] = save_color
        hook.cleanup = cleanup
        #
        color_key, save_color = cx.color_key, palette[cx.color_key]
        cur_color = save_color
        #
        while (ev := hook.ev):
            if ev.type == MOUSEWHEEL:
                color_picker.brightness += params.brightness_scroll_speed * ev.y
                color_picker.brightness = clamp(color_picker.brightness, 0, 1)
                yield; continue
            if ev.type == _ACCEPT_FORWARD:
                tmp_key = alpha_scan(ev)
                if tmp_key in palette:
                    if color_key and save_color: palette[color_key] = save_color
                    color_key = tmp_key
                    save_color = palette[color_key]
                yield; continue
            #
            #if not hasattr(ev, 'pos'): yield; continue
            assert hasattr(ev, 'pos')
            cur_color = color_picker.at_pixel(ev.pos, cur_color)
            if not cur_color: yield; continue
            #
            if color_key: palette[color_key] = cur_color
            #
            if left_click(ev):
                save_color = None
                color_key = None
            elif right_click(ev):
                return
            yield
    return iter()

# def create_weave_hook(hook, context = g):
#     hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
#     c = context
#     def cleanup(): c.hints = []
#     #
#     def disambiguate_hook(hook, candidates, i_ref):
#         post_info("Several possible shapes. scroll : disambiguate. lclick : confirm", context = c)
#         hook.watched = {MOUSEWHEEL, MOUSEBUTTONDOWN, MOUSEMOTION}
#         def cleanup(): c.hints = []
#         hook.cleanup = cleanup
#         c.hints = [candidates[i_ref.get % len(candidates)].s]
#         def iter():
#             while (ev := hook.ev):
#                 if ev.type == MOUSEWHEEL:
#                     i_ref.get += ev.y
#                     i_ref.get %= len(candidates)
#                     c.hints = [ candidates[i_ref.get].s ] 
#                 elif left_click(ev):
#                     event.post(ev)
#                     return
#                 yield
#         return iter()
#     #
#     def iter():
#         hangs = [None] * 3
#         #
#         def update_hints_hook(hook):
#             hook.watched = { MOUSEMOTION }
#             def iter():
#                 while (e := hook.ev):
#                     c.hints = [ Point(h.s.divs[h.i]) for h in hangs if (h != None) ]
#                     under_cursor, m = snappy_get_point(hook.ev.pos, c)
#                     if m: c.hints.append(Point(under_cursor))
#                     if hangs[1] != None and m and m[0].s == hangs[1].s:
#                         hint_hangs = hangs[:2] + [m[0]]
#                         # c.hints.append(Weave(hint_hangs, c.weave_incrs))
#                         c.hints.append(Weave.CreateFrom3(hint_hangs, c.weave_incrs))
#                     yield
#             return iter()
#         #
#         def get_hang():
#             if not left_click(hook.ev): return 
#             #
#             _, matches = snappy_get_point(hook.ev.pos, c)
#             if not matches: 
#                 post_error("no shape under cursor", context = c)
#                 return
#             return matches
#         #####
#         hook.attach(c.dispatch.add_hook(update_hints_hook))
#         while True:
#             def assign_item(seq, i, assignment): # `seq[i] := assignment` is illegal
#                 seq[i] = assignment
#                 return seq[i]
#             #
#             for i in range(2):
#                 while (matches := get_hang()) is None: yield
#                 if len(matches) == 1:
#                     hangs[i] = matches[0]
#                 else:
#                     i_hang = Rec(get = 0)
#                     hook.attach(c.dispatch.add_hook(disambiguate_hook, matches, i_hang))
#                     yield
#                     hangs[i] = matches[i_hang.get]
#                 yield
#             #
#             while True:
#                 while (matches := get_hang()) is None: yield
#                 try: hangs[2] = next(hg for hg in matches if hg.s == hangs[1].s)
#                 except StopIteration: 
#                     post_error("must belong to same shape", context = c)
#                     continue
#                 break
#             #
#             new_weave = Weave.CreateFrom3(hangs, c.weave_incrs)
#             if hasattr(c, 'color_key') and hasattr(c, 'palette'):
#                 new_weave.set_color(c.color_key, c.palette)
#             c.weaves.append(new_weave)
#             hangs, c.hints = [None] * 3, [] # reset
#             yield
#     return iter()
#
