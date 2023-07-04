from flow import *
from pygame import *
from view import View

def g_init():
    "init pygame and set-up globals"
    init() # from pygame
    g.screen = display.set_mode((1000, 1000))
    g.clock = time.Clock()
    g.shapes = []
    g.hints = [] 
    g.view = View()
    g.dispatch = EvDispatch()
    g.weave_incrs = (1, 1)
    #g.weave_colors = []

def main():
    g_init()
    running = True
    g.dispatch.add_hook(zoom_hook)
    g.dispatch.add_hook(menu_dispatch_hook)
    while running:
        if event.get(QUIT):
            quit()
            return
        g.dispatch.dispatch(event.get())
        g.screen.fill( (0,0,0) )
        for s in g.shapes:
            s.draw(g.screen, g.view)
        for s in g.hints:
            s.draw(g.screen, g.view, color = Color(128, 32, 32))
        display.flip()
        g.clock.tick(60);
    quit() # from pygame

# Run
main()
