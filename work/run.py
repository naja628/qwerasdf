from pygame import *
from itertools import chain
from numpy import pi

import params
from util import eprint
from flow import *
from view import View
from text import TextArea, post_info
from save import save, save_path
from miniter import miniter_exec
from color_picker import ColorPicker

def g_init():
    "init pygame and set-up globals"
    init() # from pygame
    g.screen = display.set_mode(params.start_dimensions)
    display.set_caption("QWERASDF")
    g.clock = time.Clock()
    g.shapes = []
    g.hints = [] 
    g.view = View()
    g.dispatch = EvDispatch()
    g.weave_incrs = (1, 1)
    g.weaves = []
    g.text_area = TextArea(width = display.get_window_size()[1])
    g.selected = []
    g.menu = Menu()
    g.palette = params.start_palette
    g.color_key = 'Q'
    g.show_palette = False
    g.default_rotation = 2 * pi / 6
    g.color_picker = ColorPicker(params.start_dimensions[0], (0, 0), params.min_pick_saturation)
    g.show_color_picker = False
    #g.show_color_picker = True # debug
    g.QUIT = False


def draw_palette(palette, selected = None, label_color = params.background):
    font_ = font.SysFont(('MonoSpace', None), params.font_size * 15 // 10 )
    widths = []
    # get size:
    for key in palette.keys(): # can't multiply because kerning
        widths.append(font_.size(f" {key} ")[0])
    surf = Surface(( sum(widths), font_.size('')[1] ))
    # render:
    offset = 0
    for (width, (key, bg)) in zip(widths, palette.items()):
        label = f"*{key}*" if selected == key else f" {key} " # might cause kering problems
        box = font_.render(label, True, label_color, bg)
        surf.blit(box, (offset, 0))
        offset += width
    return surf
    
def main():
    g_init()
    post_info("WHEEL: zoom | RCLICK: move the view")
    g.dispatch.add_hook(zoom_hook)
    g.dispatch.add_hook(click_move_hook)
    g.dispatch.add_hook(menu_hook)
    if (os.path.exists(save_path(params.recover_filename))):
        post_info(f"recovery file exists: try 'lo ! {params.recover_filename}'")
    #
    try:
        with open(params.dotrc) as rc:
            for line in rc:
                if line.strip() == '' or line.strip()[0] == '#': continue
                miniter_exec(line, g)
    except: pass
    #
    try:
        first_quit_request = False
        while not g.QUIT:
            if event.get(QUIT):
                if not first_quit_request:
                    post_info('Will quit without saving. Click again to confirm')
                    first_quit_request = True
                else:
                    break
            g.dispatch.dispatch(event.get())
            g.screen.fill( (0,0,0) )
            # draw shapes
            for thing in chain(g.shapes, g.weaves):
                thing.draw(g.screen, g.view)
            # draw selection on top using other color
            for sel in g.selected:
                sel.draw(g.screen, g.view, color = params.select_color)
            # draw visual hints in red
            for hint in g.hints:
                hint.draw(g.screen, g.view, color = params.hint_color)
            # menu, text
            g.menu.show()
            text_surf = g.text_area.render()
            text_y = display.get_window_size()[1] - text_surf.get_height() - 1
            g.screen.blit(text_surf, (0, text_y))
            # palette "widget"
            if g.show_palette:
                palette_surf = draw_palette(g.palette, g.color_key)
                g.screen.blit(palette_surf, (0, text_y - palette_surf.get_height()))
            # ColorPicker "widget"
            if g.show_color_picker:
                picker_surf = g.color_picker.get_surf()
                g.screen.blit(picker_surf, g.color_picker.corner)
            #
            display.flip()
            g.clock.tick(60);
        quit() # from pygame
    except:
        save(save_path(params.recover_filename), overwrite_ok = True)
        eprint('QWERASDF: Unexpected Fatal Error. Recovery save succesful')
        raise

# Run
main()
