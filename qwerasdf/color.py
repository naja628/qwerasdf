from pygame import *
import numpy as np

from .params import params, ptol, ltop
from .util import clamp

# Simple Palette
# def draw_palette(palette, selected = None, label_color = params.background):
#     # TODO kerning is not a problem bc monospace
#     font_ = font.SysFont(('MonoSpace', None), params.font_size * 15 // 10 )
#     widths = []
#     # get size:
#     for key in palette.keys(): # can't multiply because kerning
#         widths.append(font_.size(f" {key} ")[0])
#     surf = Surface(( sum(widths), font_.size('')[1] ))
#     # render:
#     offset = 0
#     for (width, (key, bg)) in zip(widths, palette.items()):
#         label = f"*{key}*" if selected == key else f" {key} " # might cause kering problems
#         box = font_.render(label, True, label_color, bg)
#         surf.blit(box, (offset, 0))
#         offset += width
#     return surf

def draw_palette(palette, selected = None, label_color = params.background):
    _font = font.SysFont(('MonoSpace', None), params.font_size * 15 // 10 )
    #
    n = len(palette.keys())
    width = _font.size(" X ")[0]
    surf = Surface(( n * width, _font.size('')[1] ))
    offset = 0
    for (key, bg) in palette.items():
        label = f"*{ptol(key)}*" if selected == key else f" {ptol(key)} "
        box = _font.render(label, True, label_color, bg)
        surf.blit(box, (offset, 0))
        offset += width
    return surf
    
# Rainbow Color Picker
def lerp(t, u, v):
    return (1 - t) * u + t * v 

def rainbow_row(width, lum, sat):
    rainbow6 = np.array(
            [[255, 0, 0], [255, 255, 0], [0, 255, 0], [0, 255, 255], [0, 0, 255], [255, 0, 255]])
    white = np.array([255, 255, 255])
    black = np.zeros(3)
    huepoints = np.array([lerp(lum, black, lerp(sat, white, hue)) for hue in rainbow6], dtype = int)
    sixths = [ 
            np.linspace(
                huepoints[i], 
                huepoints[(i+1)%6], 
                int((width+i)//6), 
                endpoint = False,
                dtype = int)
            for i in range(6)]
    return np.concatenate(sixths)

def rainbow_array(width, height, lum, min_sat = 0, max_sat = 1):
    return np.linspace(
            rainbow_row(width, lum, min_sat), 
            rainbow_row(width, lum, max_sat), 
            height, 
            axis = 1,
            dtype = int)

class ColorPicker:
    def __init__(self, width, height, corner = (0, 0), min_sat = 0, display_lum = 0.6):
        self.corner = corner
        self.display_lum = display_lum
        self.reset(width, height, corner, min_sat, display_lum)
    #
    def reset(self, width, height, corner = (0, 0), min_sat = 0, display_lum = 0.6):
        self.corner = corner or self.corner
        self.display_lum = display_lum
        self.array = rainbow_array(width, height, display_lum, min_sat, 1.0)
        self.set_surf(width, height)
        self.render()
        return self
    #
    def set_surf(self, width, height):
        self.surf = Surface(( width, height ))
    #
    def get_surf(self): return self.surf
    #
    def render(self):
        width, height = self.surf.get_size()
        pix_array = PixelArray(self.surf)
        for y in range(height):
            for x in range(width):
                pix_array[x, y] = Color(self.array[x, y])
        pix_array.close()
    #
    def _at_rel_pixel(self, pos, lum = None, clamp = False):
        lum = lum or self.display_lum
        width, height = self.surf.get_size()
        x, y = pos
        if clamp:
            pos = clamp(x, 0, width - 1), clamp(y, 0, height - 1)
        elif not (0 <= x < width and 0 <= y < height):
            return None
        return Color(self.array[x, y] * (1 / lum))
    #
    def at_pixel(self, pos, clamp = False, corner = None, lum = None):
        corner = corner or self.corner
        relpos = pos[0] - corner[0], pos[1] - corner[1]
        return self._at_rel_pixel(relpos, clamp = clamp)
    ###

