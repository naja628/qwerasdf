from pygame import *
from itertools import chain

from flow import *
from view import View
from text import TextArea

def g_init():
    "init pygame and set-up globals"
    init() # from pygame
    g.screen = display.set_mode((800, 800))
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
    #g.weave_colors = []

def main():
    g_init()
    running = True
    g.dispatch.add_hook(zoom_hook)
    g.dispatch.add_hook(menu_hook, g.menu)
    while running:
        if event.get(QUIT):
            quit()
            return
        g.dispatch.dispatch(event.get())
        g.screen.fill( (0,0,0) )
        for thing in chain(g.shapes, g.weaves):
            thing.draw(g.screen, g.view)
        #
        for sel in g.selected:
            hint.draw(g.screen, g.view, color = params.select_color)
        #
        for hint in g.hints:
            hint.draw(g.screen, g.view, color = params.hint_color)
        #
        text_img = g.text_area.render()
        text_y = display.get_window_size()[1] - text_img.get_height() - 1
        g.screen.blit(text_img, (0, text_y))
        #
        display.flip()
        g.clock.tick(60);
    quit() # from pygame

# Run
main()
