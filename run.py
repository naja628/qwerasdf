from pygame import *
from itertools import chain

from flow import *
from view import View
from text import TextArea
from save import save, load

def g_init():
    "init pygame and set-up globals"
    init() # from pygame
    g.screen = display.set_mode((800, 800))
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
    g.colors = Rec(palette = params.start_palette, key = 'Q', show = False)

def draw_palette(palette, label_color = Color(0, 0, 0)):
    font_ = font.SysFont(('MonoSpace', None), params.font_size * 15 // 10 )
    widths = []
    for key in palette.keys(): # can't multiply because kerning
        widths.append(font_.size(f" {key} ")[0])
    surf = Surface(( sum(widths), font_.size('')[1] ))
    offset = 0
    for (width, (key, bg)) in zip(widths, palette.items()):
        box = font_.render(f" {key} ", True, label_color, bg)
        surf.blit(box, (offset, 0))
        offset += width
    return surf
    
def main():
    g_init()
    running = True
    g.dispatch.add_hook(zoom_hook)
    g.dispatch.add_hook(menu_hook, g.menu)
    while running:
        if event.get(QUIT):
            save('foo.qw')
            quit()
            return
        g.dispatch.dispatch(event.get())
        g.screen.fill( (0,0,0) )
        for thing in chain(g.shapes, g.weaves):
            thing.draw(g.screen, g.view)
        #
        for sel in g.selected:
            sel.draw(g.screen, g.view, color = params.select_color)
        #
        for hint in g.hints:
            hint.draw(g.screen, g.view, color = params.hint_color)
        #
        text_img = g.text_area.render()
        text_y = display.get_window_size()[1] - text_img.get_height() - 1
        g.screen.blit(text_img, (0, text_y))
        if g.colors.show:
            palette_img = draw_palette(g.colors.palette)
            g.screen.blit(palette_img, (0, text_y - palette_img.get_height()))
        #
        display.flip()
        g.clock.tick(60);
    quit() # from pygame

# Run
main()
