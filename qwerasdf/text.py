from pygame import *

from .params import params
from .util import Rec

# class TextArea():
#     def __init__(self, width = 1080, numlines = 6):
#         self.background = params.background
#         self.font = font.SysFont(("MonoSpace", None), params.font_size)
#         self.line_height = self.font.size('')[1]
#         self.lines = numlines * [Rec(text = '', color = params.text_color)]
#         self.set_surface(width)
#     #
#     def reset(self):
#         self.lines = numlines * [Rec(text = '', color = params.text_color)]
#         self.surf.fill(params.background)
#     #
#     def set_surface(self, width):
#         self.surf = Surface((width, len(self.lines) * self.line_height))
#     #
#     def set_line(self, i, text, color = params.text_color):
#         self.lines[i] = Rec(text = text, color = color)
#     #
#     def render(self):
#         self.surf.fill(params.background)
#         for i, line in enumerate(self.lines):
#             s = self.font.render(line.text, True, line.color, self.background)
#             self.surf.blit(s, (0, i * self.line_height))
#         return self.surf
#     ###
# 

class Section:
    def __init__(self, min_lines, max_lines, color = Color(255, 255, 255), wrap = True):
        self.minmax = (min_lines, max_lines)
        self.color = color
        self.lines = []
        self.wrap = wrap

def _flatten1(l):
    ret = []
    for x in l: ret.extend(x)
    return ret

class TextArea:
    def __init__(self, fontsize, width, bg, sections = {}):
        self.width = width
        self.sections = sections
        #
        self.font = font.SysFont(("MonoSpace", None), fontsize)
        self.ch_dim = self.font.size('x')
        self.bg = bg
        self.surf = None
    #
    def set_sections_abcw(self, sections):
        self.sections = { 
                name: Section(a, b, c, w) 
                for (name, ((a, b), c, w)) in sections.items() }
    #
    def set_width(self, width):
        self.width = width
        self._render()
    #
    def write_section(self, section, lines):
        self.sections[section].lines = lines
        self._render()
    #
    def display_lines(self, section):
        lines = self.sections[section].lines
        #
        cpl = self.width // self.ch_dim[0] # chars per line
        if self.sections[section].wrap:
            def split_line(line):
                return [line[i:i+cpl] for i in range(0, len(line), cpl)]
            # lines = [ *split_line(line) for line in lines] # saddly python doesn't like this syntax
            lines = _flatten1([ split_line(line) for line in lines])
        else:
            lines = [line[0:cpl] for line in lines]
        a, b = self.sections[section].minmax
        if len(lines) < a: lines = lines + [''] * (a - len(lines)) 
        elif len(lines) > b: lines = lines[:b]
        #
        return lines
    #
    def _render(self):
        colorlines = _flatten1([ [(line, se_v.color) for line in self.display_lines(se_k)] 
            for se_k, se_v in self.sections.items() ])
        surf = Surface((self.width, len(colorlines) * self.ch_dim[1]))
        surf.fill(self.bg)
        for i, (line, color) in enumerate(colorlines):
            s = self.font.render(line, True, color, self.bg)
            surf.blit(s, (0, i * self.ch_dim[1]))
        self.surf = surf
        return surf
    # 
    def render(self):
        if not self.surf: self._render()
        return self.surf


