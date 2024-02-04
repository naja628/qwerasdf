from pygame import *
from math import pi

from color import draw_palette, ColorPicker
from hooks import EvDispatch
from text import TextArea
from hooks import *

_menu_layout = ['QWER', 'ASDF', 'ZXCV']
_nested_menu = {
        'S': ("Selection", 
            { 'E': "Unweave", 'R': "Remove",
                'A': "Transform", 'S': "Copy-Transform", 'D': "Move", 'F': "Copy-Move" }),
        'D': ("Create Shapes",
            {'A': "New Point", 'S': "New Segment", 'D': "New Circle"}),
        'F': ("Draw Weaves",
            {'S': "Select Color", 'W': "Color Picker"}),
        }

_pinned_menu = {'Z': "Camera", 'X': "Menu Top", 'C': "Command"}

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
    def overhook(hook_fun, *a, **ka):
        subhook = context.dispatch.add_hook(hook_fun, *a, **ka)
        if state.main_hook: state.main_hook.attach(subhook)
        else: state.main_hook = subhook
    #
    def inner(ev):
        if ev.key == K_SPACE:
            menu.go_path("")
            set_hook(None)
        key = alpha_scan(ev)
        menu_item = menu.go(key)
        match menu_item:
            # Pinned
            case "Camera":
                overhook(change_view_hook, context)
            case "Menu Top":
                menu.go_path("")
                set_hook(None)
            case "Command": overhook(miniter_hook, context)
            # Selection
            case "Selection": set_hook(select_hook, context)
            case "Remove": delete_selection(context)
            case "Unweave": unweave_inside_selection(context)
            case "Move": overhook(move_selection_hook, context)
            case "Copy-Move": overhook(move_selection_hook, context, want_copy = True)
            case "Transform": overhook(transform_selection_hook, context)
            case "Copy-Transform": overhook(transform_selection_hook, context, want_copy = True)
            # Shapes
            case "New Point": set_hook(create_points_hook, context)
            case "New Segment": set_hook(create_lines_hook, context)
            case "New Circle": set_hook(create_circles_hook, context)
            # Weaves
            case "Draw Weaves": set_hook(create_weaves_hook, context)
            case "Select Color": overhook(select_color_hook, context)
            case "Color Picker": overhook(color_picker_hook, context)
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
    cx.menubox = TextArea(dimensions[0], numlines = 3)
    cx.show_menu = True
    cx.bottom_text = TextArea(dimensions[0], numlines = 3)
    cx.TERMLINE, cx.ERRLINE, cx.INFOLINE = 0, 1, 2 # line numbers, maybe move to `params`?
    #
    cx.view = View()
    cx.weave_layer = Surface(dimensions)
    cx.screen = display.set_mode(params.start_dimensions)
    display.set_caption('QWERASDF')
    #
    cx.default_rotation = 2 * pi / 6
    return cx

def main():
    init() #pygame
    g = init_context(params.start_dimensions)
    #
    g.dispatch.add_hook(zoom_hook, g)
    g.dispatch.add_hook(menu_hook, g)
    g.dispatch.add_hook(click_move_hook, g)
    #
    try:
        with open(params.dotrc) as rc:
            for line in rc:
                if line.strip() == '' or line.strip()[0] == '#': continue
                miniter_exec(line, g)
    except: pass
    #
    clock = time.Clock()
    g.QUIT = False
    while not g.QUIT:
        if event.get(QUIT):
            g.QUIT = True
        evs = event.get()
        # TODO maybe do several `event.get` calls: 
        # 1: things we don't care about, 2: MOUSEMOTION, keep only last, 3: send latter + rest to `dispatch`
        # point: avoid computing `snappy_get_point` for every intermediate MOUSEMOTION
        g.dispatch.dispatch(evs)
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
        # for we in g.weaves: we.draw(g.screen, g.view)
        for sh in g.shapes: sh.draw(g.screen, g.view, params.shape_color)
        for sel in g.selected: sel.draw(g.screen, g.view, color = params.select_color)
        for hi in g.hints: hi.draw(g.screen, g.view, color = params.hint_color)
        g.screen.unlock()
        #
        # bottom "widgets"
        bottom_elements = []
        if g.show_palette: bottom_elements.append(draw_palette(g.palette, g.color_key))
        if g.show_menu: bottom_elements.append(g.menu.render(g.menubox))
        bottom_elements.append(g.bottom_text.render())
        #
        elt_y = g.screen.get_size()[1]
        for elt in reversed(bottom_elements):
            elt_y -= elt.get_size()[1]
            g.screen.blit(elt, (0, elt_y))
        #
        if g.show_picker:
            picker_surf = g.color_picker.get_surf()
            g.screen.blit(picker_surf, g.color_picker.corner)
        display.flip()
        clock.tick(60);
    quit() # from pygame

main()
exit()