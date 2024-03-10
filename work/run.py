from pygame import *
from math import pi
from os import path

from util import eprint
from color import draw_palette, ColorPicker
from hooks import EvDispatch
from text import TextArea
from hooks import *
from context import delete_selection, unweave_inside_selection, MENU_RESET
from menu import Menu
from save import Autosaver, save_path, save, save_buffer
from params import params
from grid import Grid

_sho = Menu.Shortcut
_menu_layout = ['QWER', 'ASDF', 'ZXCV']
_nested_menu = {
        'A': ("Grid", 
            {   'A': "Grid on/off", 'S': "Grid +/- sparse", 'D': "Grid recenter", 'F': "Grid phase"}),
        'S': ("Selection", 
            {   'W': "Visual", 'E': "Unweave", 'R': "Remove",
                'A': "Transform", 'S': "Copy-Transform", 'D': "Move", 'F': "Copy-Move" }),
        'D': ("Create Shapes",
            {   'Q': "New Point", 'W': "New Polyline",
                'A': "New Arc",   'S': "New Segment", 'D': "New Circle", 'F': ("Draw Weaves", _sho('F'))}),
        'F': ("Draw Weaves",
            {   'W': "Color Picker", 'E': "Select Color",
                                     'D': ("Create Shape", _sho('D')), 'F': ("Draw Weaves", _sho('F'))}),
        }
_pinned_menu = {'Z': "Camera", 'X': "Menu Top", 'C': "Command", 'V': "Rewind"}

_menuaction_info = { # What the user has to do AFTER, not what it does
        "New Arc": "LCLICK * 3: place center, start, end | RCLICK: invert rotation",
        "Rewind": "WHEEL -> Rewind | CLICK -> done",
        "Camera": "WHEEL -> zoom | RCLICK, RCLICK: grab, then release canvas | LCLICK -> Done",
        "Command": "Commandline. 'ls' -> list available commands | CTRL-C -> close",
        "New Point": "LCLICK: place",
        "New Segment": "LCLICK, LCLICK: place endpoints",
        "New Polyline": "LCLICK: add point / (if on start) connect and finish | RCLICK: finish without connecting",
        "New Circle": "LCLICK, LCLICK: place center, then point on perim | RCLICK: invert placement order",
        "Draw Weaves": "LCLICK on 1st shape then LCLICK * 2 on 2nd shape. | RCLICK: \"no, the other way\"",
        "Select Color": "QWERASDF (keyboard) -> pick color",
        "Selection": "LCLICK -> select under cursor | RCLICK -> toggle-selected under cursor",
        "Move": "LCLICK -> confirm (shape will move) | RCLICK -> cancel",
        "Copy-Move": "LCLICK -> confirm (new copy will be created) | RCLICK -> cancel",
        "Transform": "LCLICK -> confirm (shape will change) | RCLICK -> cancel",
        "Cp-Transform": "LCLICK -> confirm (new copy will be created) | RCLICK -> cancel",
        "Visual": "LCLICK -> apply change | RCLICK -> put copy",
        "Color Picker": "LCLICK -> apply | RCLICK -> close | QWERASDF -> change affected color | WHEEL -> adjust brightness",
        # TODO grid 
        }


def menu_hook(hook, context):
    setup_hook(hook, {KEYDOWN, MENU_RESET})
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
    def overhook(hook_fun, *a, **ka):
        subhook = context.dispatch.add_hook(hook_fun, *a, **ka)
        if state.main_hook: state.main_hook.attach(subhook)
        else: state.main_hook = subhook
    #
    def inner(ev):
        if ev.type == MENU_RESET:
            menu_item = menu.go_path(ev.path)
        else:
            if ev.key == K_SPACE:
                menu.go_path("")
                set_hook(None)
                return
            key = alpha_scan(ev)
            menu_item = menu.go(key)
        try: post_info( _menuaction_info[menu_item], context)
        except KeyError: pass
        match menu_item:
            # Pinned
            case "Menu Top":
                menu.go_path("")
                set_hook(None)
            case "Camera": overhook(change_view_hook, context)
            case "Command": overhook(miniter_hook, context)
            case "Rewind": set_hook(rewind_hook, context)
            # Selection
            case "Selection": set_hook(select_hook, context)
            case "Remove": delete_selection(context)
            case "Unweave": unweave_inside_selection(context)
            case "Move": overhook(move_selection_hook, context)
            case "Copy-Move": overhook(move_selection_hook, context, want_copy = True)
            case "Transform": overhook(transform_selection_hook, context)
            case "Copy-Transform": overhook(transform_selection_hook, context, want_copy = True)
            case "Visual": overhook(interactive_transform_hook, context)
            # Shapes
            case "New Point": set_hook(create_points_hook, context)
            case "New Segment": set_hook(create_lines_hook, context)
            case "New Circle": set_hook(create_circles_hook, context)
            case "New Arc": set_hook(create_arcs_hook, context)
            case "New Polyline": set_hook(create_poly_hook, context)
            # Weaves
            case "Draw Weaves": set_hook(create_weaves_hook, context)
            case "Select Color": overhook(select_color_hook, context)
            case "Color Picker": overhook(color_picker_hook, context)
            # Grid
            case "Grid on/off": toggle_grid(context)
            case "Grid +/- sparse": set_hook(grid_sparseness_hook, context)
            case "Grid recenter": set_hook(grid_recenter_hook, context)
            case "Grid phase": set_hook(grid_phase_hook, context)
            #
            case _: set_hook(None) # Necessary? Good?
    #
    hook.event_loop(inner)

def init_context(dimensions):
    cx = Rec()
    #
    cx.dispatch = EvDispatch()
    #
    cx.shapes = []
    cx.selected = []
    cx.hints = []
    #
    cx.palette = params.start_palette
    cx.color_key = 'Q'
    cx.show_palette = True
    cx.color_picker = ColorPicker(dimensions[0], dimensions[0] // 8, (0, 0), params.min_pick_saturation) 
    cx.show_picker = False
    #
    #cx.color_weave_pairs = []
    cx.weaves = []
    cx.weave_colors = {}
    cx.pending_weaves = []
    cx.redraw_weaves = True
    cx.weavity = (1, 1)
    cx.weaveback = True
    #
    cx.menu = Menu(_nested_menu, _pinned_menu, _menu_layout)
    #
    cx.show_menu = True
    sections = {
            'menu': ((0, 3), params.text_color, False),
            'term': ((0, 1), params.term_color, False),
            'error': ((0,2), params.error_text_color, True),
            'info': ((0, 4), params.text_color, True),
            }
    cx.text = TextArea(params.font_size, params.start_dimensions[0], params.background)
    cx.text.set_sections_abcw(sections)
    #
    cx.view = View(corner = (-1, 1))
    cx.weave_layer = Surface(dimensions)
    cx.screen = display.set_mode(params.start_dimensions)
    display.set_caption('QWERASDF')
    #
    cx.default_rotation = 2 * pi / 6
    #
    cx.df_divs = {'circle': 120, 'line': 20, 'arc': 20, 'poly': 60}
    #
    cx.last_save_buffer = ''
    try:
        cx.autosaver = Autosaver(path.join(params.autosave_dir, 'default'), 
                                 pulse = params.autosave_pulse)
    except Autosaver.DirectoryBusyError:
        post_error(
                "`default` session in use. Won't be able to undo." 
                "Use `session <name>` to connect to another session", 
                cx)
        cx.autosaver = None
    #
    cx.grid = Grid()
    cx.grid_on = False
    return cx

def del_context(context):
    if context.autosaver: context.autosaver.finish()

def main():
    init() #pygame
    g = init_context(params.start_dimensions)
    g.last_save_buffer = save_buffer(g, extra = {'session'})
    # Base actions
    g.dispatch.add_hook(zoom_hook, g)
    g.dispatch.add_hook(autosave_hook, g)
    g.dispatch.add_hook(click_move_hook, g)
    g.dispatch.add_hook(menu_hook, g)
    # Read rc:
    for filename in params.dotrc_path:
        try:
            with open(filename) as rc:
                for line in rc:
                    if line.strip() == '' or line.strip()[0] == '#': continue
                    miniter_exec(line, g)
            break
        except: continue
    # Main loop:
    clock = time.Clock()
    g.QUIT = False
    if path.isfile(path.join(params.save_dir, params.recover_filename)):
        post_info("Recovery save found. Try `recover` command", g)
    try:
        while not g.QUIT:
            if event.get(QUIT):
                g.QUIT = True
            evs = event.get()
            # TODO maybe do several `event.get` calls: 
            # 1: things we don't care about, 2: MOUSEMOTION, keep only last, 3: send latter + rest to `dispatch`
            # point: avoid computing `snappy_get_point` for every intermediate MOUSEMOTION
            g.dispatch.dispatch(evs)
            g.dispatch.dispatch([event.Event(LOOP)])
            #
            # Draw Weaves :
            g.weave_layer.lock()
            if g.redraw_weaves:
                g.weave_layer.fill(params.background)
                g.pending_weaves += g.weaves
                g.weaves = []
                g.redraw_weaves = False
            for we in g.pending_weaves:
                ckey = g.weave_colors[we]
                we.draw(g.weave_layer, g.view, color = g.palette[ckey])
                g.weaves.append(we)
            g.weave_layer.unlock()
            g.pending_weaves = []
            #g.screen.fill(params.background) # not needed?
            g.screen.blit(g.weave_layer, (0, 0))
            #
            # Draw Rest: (on top)
            g.screen.lock()
            # draw grid:
            # note: update may be slightly "too late" if the view has changed this frame
            #  but this avoids re-doing expensive computations and is probably not perceptible
            if g.grid_on:
                g.grid.update(g.view, g.screen.get_size())
                g.grid.render(g.screen, params.background, params.grid_color)
            # draw shapes, etc
            for sh in g.shapes: sh.draw(g.screen, g.view, params.shape_color)
            for sel in g.selected: sel.draw(g.screen, g.view, color = params.select_color)
            for hi in g.hints: hi.draw(g.screen, g.view, color = params.hint_color)
            g.screen.unlock()
            #
            # bottom "widgets"
            bottom_elements = []
            if g.show_palette: bottom_elements.append(draw_palette(g.palette, g.color_key))
            if g.show_menu: g.menu.render(g.text)
            bottom_elements.append(g.text.render())
            #
            elt_y = g.screen.get_size()[1]
            for elt in reversed(bottom_elements):
                elt_y -= elt.get_size()[1]
                g.screen.blit(elt, (0, elt_y - params.bottom_margin))
            #
            if g.show_picker:
                picker_surf = g.color_picker.get_surf()
                g.screen.blit(picker_surf, g.color_picker.corner)
            display.flip()
            clock.tick(60);
    except:
        save(save_path(params.recover_filename), g, overwrite_ok = True)
        eprint('Unexpected Fatal Error. Recovery save succesful')
        raise
    finally:
        del_context(g)
        quit() # from pygame

main()
exit()
