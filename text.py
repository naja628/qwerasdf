from pygame import *
from params import params
from context import g
from util import Rec

MENULINE1 = 0; TERMLINE = 3; ERRLINE = 4; INFOLINE = 5
class TextArea():
    def __init__(self, width = 1080, numlines = 6):
        self.background = params.background
        self.font = font.SysFont(("MonoSpace", None), params.font_size)
        self.line_height = self.font.size('')[1]
        self.set_surface(width)
        self.lines = numlines * [Rec(text = '', color = params.text_color)]
    #
    def reset(self):
        self.lines = numlines * [Rec(text = '', color = params.text_color)]
        self.surf.fill(params.background)
    #
    def set_surface(self, width):
        self.surf = Surface((width, 6 * self.line_height))
    #
    def set_line(self, i, text, color = params.text_color):
        self.lines[i] = Rec(text = text, color = color)
    #
    def render(self):
        self.surf.fill(params.background)
        for i, line in enumerate(self.lines):
            s = self.font.render(line.text, True, line.color, self.background)
            self.surf.blit(s, (0, i * self.line_height))
        return self.surf
    ###

def post_error(msg, linenum = ERRLINE, context = g):
    g.text_area.set_line(linenum, f"Error: {msg}", params.error_text_color)

def post_info(msg, linenum = INFOLINE, context = g):
    g.text_area.set_line(linenum, f"Hint: {msg}")

