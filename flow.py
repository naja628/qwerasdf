import os
from pygame import *

from shape import *
from context import g
from util import dist, Rec, unique_closure
# from params import params
import params
import text
from text import post_error, MENULINE1, TERMLINE
from save import *

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
        context.selected = shapes

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

def zoom_hook(hook, factor = params.zoom_factor, context = g):
    hook.watched = { MOUSEWHEEL }
    def iter():
        while e := hook.ev:
            context.view.zoom(mouse.get_pos(), factor ** e.y)
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
    c = context
    def cleanup(): c.show_palette = False
    hook.cleanup = cleanup
    #
    c.show_palette = True
    def iter():
        if (ch := alpha_scan(hook.ev)) in c.palette:
            c.color_key = ch
        return
        assert False; yield
    return iter()

def select_hook(hook, context = g):
    # left-click -> select ONE, right-click -> toggle selected
    hook.watched = { MOUSEBUTTONDOWN, MOUSEMOTION }
    def cleanup(): context.selected = []; context.hints = []
    hook.cleanup = cleanup
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
def move_selection_hook(): pass
def transform(): pass

############ MINITER #######################à
def term_exec(cmd, context = g):
    cmd_map = terminal_command_map
    #
    def parse_cmd(cmd):
        # maybe parse opts?
        # maybe allow some quoting
        def autocast(s):
            assert len(s) > 0 # ok bc comes from `split`
            if s[0] == '-' or '0' <= s[0] <= '9':
                if '.' in s:
                    return float(s)
                else:
                    return int(s)
            else:
                return s
        #
        def parse_kwarg(kwarg):
            split = kwarg.find('=')
            return kwarg[:split], autocast(kwarg[split + 1:])
        #
        [cmd, *tokens] = cmd.split()
        args = [autocast(tok) for tok in tokens if '=' not in tok]
        kwarg_list = [parse_kwarg(tok) for tok in tokens if '=' in tok]
        kwargs = { k : v for (k, v) in kwarg_list }
        kwargs['_env'] = Rec(context = context, cmd = cmd)
        return cmd, args, kwargs
    #
    try:
        cmd, args, kwargs = parse_cmd(cmd)
        if not cmd in cmd_map:
            post_error("Command not found", context = context)
            return 1
        cmd_map[cmd](*args, **kwargs)
        return 0
    except BaseException as e:
        try:
            post_error(str(e), context = context)
        except:
            post_error("unexpected error", context = context)
        return 1

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
                    status = term_exec(command)
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

############## CMDS (COMMANDS) ######################
class Exn(Exception): pass

def color_cmd(*args, _env):
    palette = _env.context.palette
    try:
        key = args[0].upper()
        if key not in palette: raise RuntimeError
    except:
        raise Exn("first argument must be a valid color key")
    #
    def set_rgb(r, g, b):
        palette[key] = Color(r, g, b)
    #
    def set_hex(hexstr):
        hexstr = str(hexstr)
        if hexstr[:2].lower() == "0x":
            hexstr = hexstr[2:]
        hexstr = hexstr.rjust(6, '0')
        [r, g, b] = [int(hexstr[i:i+2], 16) for i in range(0, 6, 2)]
        set_rgb(r, g, b)
    #
    try:
        match args[1:]:
            case []: _env.context.color_key = key
            case [hexcolor]: set_hex(hexcolor)
            case [r, g, b]: set_rgb(r, g, b)
    except BaseException as e:
        cmd = _env.cmd
        raise Exn(f"usage: {cmd} key OR {cmd} key r g b OR {cmd} hex")
    #

def show_palette_cmd(*, _env):
    _env.context.show_palette = not _env.context.show_palette

def set_div_cmd(n, *, _env):
    if not type(n) is int:
        raise Exn(f"usage: {_env.cmd} <new number of nails (int)>")
    if n <= 0:
        raise Exn("number must be at least 1")
    for sh in _env.context.selected:
        sh.set_divs(n)

def set_weavity_cmd(inc0, inc1, *, _env):
    if inc1 == 0:
        raise Exn("cant't be _, 0")
    if (type(inc0), type(inc1)) != (int, int):
        raise Exn("usage: {_env.cmd} bound_increment, free_increment")
    _env.context.weave_incrs = (inc0, inc1)

def fullscreen_cmd(*, _env):
    g.screen = display.set_mode(flags = FULLSCREEN)

def resize_cmd(w, h, *, _env):
    try:
        if w < 300 or h < 300 or w > 9000 or h > 9000:
            raise Exn("bad dimensions")
        g.screen = display.set_mode((w, h))
    except BaseException:
        raise Exn("usage: {_env.cmd} width height")

def exit_cmd(save_or_bang, *, _env):
    try:
        if save_or_bang != '!':
            save(save_path(save_or_bang), overwrite_ok = True)
        g.QUIT = True
    except: raise Exn("usage: {_env.cmd} save_to OR {_env.cmd} !}")

_last_save_filename = None
def save_cmd(*a, _env):
    global _last_save_filename
    usage_msg = f"usage:  {_env.cmd} file OR {_env.cmd} ! OR {_env.cmd} ! file"
    print(a, len(a), 1 <= len(a) <= 2)
    if not (1 <= len(a) <= 2):
        raise Exn(usage_msg)
    print('here')
    try:
        if a[0] == '!':
            file = _last_save_filename if len(a) == 1 else a[1]
        else:
            file = a[0]
        if file == None: raise Exn("No previous savename")
        overwrite_ok = (a[0] == '!')
        print(overwrite_ok, file)
        save(save_path(file), overwrite_ok, _env.context)
        _last_save_filename = file
    except FileExistsError:
        raise Exn(f"'{file}' exists. to allow overwrites, use: {_env.cmd} ! {file}")
    except: 
        raise

def load_cmd(save, load, *, _env):
    usage_msg = f"Usage: {_env.cmd} save_to load_from OR {_env.cmd} ! load_from"
    if save != '!':
        try:
            save(save_path(save), overwrite_ok = False, context = _env.context)
        except FileExistsError:
            raise Exn(f"{save} exists." + usage_msg)
    #
    try:
        load_to_context(save_path(load), _env.context)
    except LoadError: raise Exn(f"Error loading {load}")

def clear_cmd(*, _env):
    for line in text.ERRLINE, text.INFOLINE:
        _env.context.text_area.set_line(line, '')
    #

def list_cmd(): pass

_tmp_cmd_map = {
        ('set_color', 'co'): color_cmd,
        ('palette', 'pal'): show_palette_cmd,
        ('exit', 'quit', 'q'): exit_cmd,
        ('set_div', 'div'): set_div_cmd,
        ('fullscreen', 'fu' ) : fullscreen_cmd,
        ('resize', 'res'): resize_cmd,
        ('weavity', 'wy'): set_weavity_cmd,
        ('save', 's'): save_cmd,
        ('load', 'lo'): load_cmd,
        ('list', 'help', 'h', 'ls'): list_cmd,
        ('clear', ): clear_cmd
        }

terminal_command_map = {}
for ks, v in _tmp_cmd_map.items():
    terminal_command_map.update({k : v for k in ks})

# h, default_rot 

# autosave_prefix, rewind
######################## MENU ########################
class Menu:
    def __init__(self):
        self._path = ""
        self.root = {
            'S': ("Select", 
                {'E': "Unweave", 'R': "Remove"} ),
            'D': ("Draw Weave", 
                {'A' : "Invert", 'S': "Select Color", 'D': "Draw Weave", 'F': "New Shape"}),
            'F': ("New Shape", 
                {'A': "New Point", 'S': "New Segment", 'D': "Draw Weave", 'F' : "New Circle"}),
        }
        self.pos = self.root # pos is always a dict
        #
        self.pinned = {'Z': "Menu Top", 'X': "Back", 'C': "Command"}
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
                    self.pos = down[1] # navigate down
                    self._path += key
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

# *** Menu Structure ***
### Pinned:
# Menu Top
# Back
# Command
#
### Nested:
# New Shape
#     New Point
#     New Segment
#     New Circle
# Select
#     Unweave
#     Remove
# Draw Weave
#     Invert
#     Swap
#     Choose Color
#

def menu_hook(hook, menu, context = g):
    hook.watched = { KEYDOWN }
    #
    c = context
    menu.show(c)
    def iter():
        top_hook = None
        def set_top_hook(hook_fun, *a, **ka):
            nonlocal top_hook
            if top_hook != None: top_hook.finish()
            if hook_fun != None: top_hook = c.dispatch.add_hook(hook_fun, *a, **ka)
            else: top_hook = None
        #
        while (ev := hook.ev):
            key = alpha_scan(ev)
            if not key:
                yield; continue
            #
            print("got menu:", key) # debug
            match menu.go(key):
                # Pinned
                case "Back":
                    if top_hook != None: set_top_hook(None) 
                    menu.up(1)
                case "Menu Top": 
                    menu.go_path("")
                    set_top_hook(None)
                case "Command":
                    # don't use set_top_hook bc we cede control
                    c.dispatch.add_hook(miniter_hook, c)
                # Create Shapes
                case "New Point": pass # TODO
                case "New Segment": set_top_hook(draw_lines_hook, c)
                case "New Circle": set_top_hook(draw_circles_hook, c)
                # Alter Selection
                case "Select": set_top_hook(select_hook, c)
                case "Unweave": unweave_selection(context = c)
                case "Remove": delete_selection(context = c)
                # Alter Weave Behavior
                case "Draw Weave": set_top_hook(create_weave_hook, c)
                case "Invert":
                    inc0, inc1 = context.weave_incrs
                    context.weave_incrs = (-inc0, inc1)
                case "Choose Color":
                    c.dispatch.add_hook(choose_color_hook, c)
                #
                case _:
                    pass
            menu.show(c)
            yield
    #
    return iter()

# # Event and dispatch
# _DETACHED = 0; _DONE = 1; _ATTACHED = 2; _JOINING = 3; _BAD = 4
# class EvHook:
#     def __init__(self, make_hook, *args, **kwargs):
#         self.status = HS.DETACHED
#         self.cleanup = lambda : None
#         self.iter = make_hook(self, *args, **kwargs)
#         assert 'watched' in self.__dict__ # should be set-up by `make_hook`
#         # self.ret = None
#     #
#     def pass_ev(self, event):
#         assert event.type in self.watched
#         self.ev = event
#         try:
#             next(self.iter)
#         except StopIteration:
#             self.finish()
#             #
#             match self.status:
#                 case _DETACHED: self.status = _DONE
#                 case _ATTACHED: self.status = _JOINING
#                 case _: self.status = _BAD
#     #
#     def finish(self):
#         self.cleanup()
#         self.watched = set()
#         self.done = True
#     #
#     def detached(): return self.status == _DETACHED
#     def done(): return self.status == _DONE
#     def attached(): return self.status == _ATTACHED
#     def joining(): return self.status == _JOINING
#     def bad(): return self.status == _BAD
#     ###
# 
# class EvDispatch: # event dispatcher
#     def __init__(self):
#         self.type_to_hook = {}
#     #
#     def add_hook(self, make_hook, *args, **kwargs):
#         new_hook = EvHook(make_hook, *args, **kwargs)
#         for type_ in new_hook.watched:
#             try:
#                 self.type_to_hook[type_].append(new_hook)
#             except KeyError:
#                 self.type_to_hook[type_] = [new_hook]
#         return new_hook
#     #
#     def dispatch1(self, ev):
#         if not ev.type in self.type_to_hook:
#             return
#         #
#         hooks = self.type_to_hook[ev.type]
#         while hooks and hooks[-1].done:
#             hooks.pop()
#         if not hooks:
#             del self.type_to_hook[ev.type]
#             return
#         #
#         hooks[-1].pass_ev(ev)
#         if hooks[-1].joining():
#             self.dispatch1(ev)
#     #
#     def dispatch(self, events):
#         for ev in events:
#             dispatch1(ev)
#     ###

# def show_menu(keypath, highlighted = '', context = g):
#     text_area = context.text_area
#     label_size = 10
#     def get_nested_label(last_key):
#         sub = nested_menu
#         for key in keypath:
#             if not key in sub:
#                 return None
#             else:
#                 sub = sub[key][1]
#         try:
#             return sub[last_key][0]
#         except KeyError:
#             return None
#     #
#     for (i, row) in enumerate(menu_layout):
#         line = "|"
#         for key in row:
#             if key in pinned_menu:
#                 label = pinned_menu[key]
#             elif label := get_nested_label(key):
#                 pass
#             else:
#                 label = None
#             if label:
#                 line += f" {key}: "
#                 line += label[:label_size].ljust(label_size, ' ')
#             else:
#                 line += ' ' * (len(" X: ") + label_size)
#             line += ' |'
#         text_area.set_line(i + MENULINE1, line)
#     ###
# 
# def menu_dispatch_hook(hook, context = g):
#     # F -> draw: F line, D circle
#     # G -> reset
#     # X -> Cancel
#     hook.watched = { KEYDOWN }
#     show_menu('')
#     #
#     def iter():
#         menu_path = ""
#         top_hook = None
#         def reset_hook():
#             if top_hook is None: return
#             else: top_hook.finish()
#         while e := hook.ev:
#             print("got menu:", alpha_scan(e))
#             match menu_path, alpha_scan(e): 
#                 case "", 'D':
#                     reset_hook()
#                     menu_path = "D"
#                     top_hook = g.dispatch.add_hook(create_weave_hook)
#                 case "D", ' ':
#                     inc0, inc1 = context.weave_incrs
#                     context.weave_incrs = (-inc0, inc1)
#                 case "", 'F':
#                     menu_path = "F"
#                 case "F", 'F':
#                     reset_hook()
#                 case "F", 'D':
#                     reset_hook()
#                     top_hook = g.dispatch.add_hook(draw_circles_hook)
#                 case _, 'G':
#                     reset_hook()
#                     menu_path = ""
#                 case _, 'X': # TODO rethink this
#                     reset_hook()
#                     menu_path = menu_path[:-1] if menu_path else ""
#                 case _, 'C':
#                     top_hook = g.dispatch.add_hook(miniter_hook)
#                 case _:
#                     pass
#             show_menu(menu_path)
#             yield
#     return iter()
# 
# Note: weird pygame "bug" (?) where pressing control+key (at KEYUP)
# very fast results in unmodified ascii control code
# (ie CTRL-c -> key = 'c', unicode = '\0x03' (ie ^C), mod = 0)
