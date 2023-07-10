from pygame import *
import numpy as np

from util import clamp
MAX_WIDTH = 700 # not a param bc setting it high makes resizes unresponsive
PICKER_RATIO = 9

# TODO: instead of rendering at every resize (unresponsive because computations are slow)
#   pre compute images of a few sizes and load them
#   probably also put the color picker in the middle (instead of left) since we don't take the full length
#   (or invert axis but a pain cuz need to find y of top of palette)

class ColorPicker:
    def __init__(self, width, corner = (0, 0), min_sat = 0):
        self.reset(width, corner, min_sat)
    #
    def reset(self, width, corner = (0, 0), min_sat = 0):
        self.min_sat = min_sat
        self.corner = corner
        self.brightness = 0.6
        try:
            if not self.width == MAX_WIDTH and width > max_with:
                self.set_surf(width)
        except:
            self.set_surf(width)
        self.render()
        return self
    #
    def set_surf(self, width = None):
        self.width = min(int(width), MAX_WIDTH) or self.width
        self.height = self.width // PICKER_RATIO
        self.surf = Surface(( self.width, self.height ))
    #
    def get_surf(self): return self.surf
    #
    def render(self):
        pix_array = PixelArray(self.surf)
        for y in range(self.height):
            for x in range(self.width):
                pix_array[x, y] = self._at_rel_pixel( (x, y) )
        pix_array.close()
    #
    def _at_rel_pixel(self, pos):
        self.brightness = clamp(self.brightness, 0, 1)
        x, y = pos
        hu, sa = x / self.width, y / self.height
        sa = sa * (1 - self.min_sat) + self.min_sat
        return Color(v_hsl(hu, sa, self.brightness))
    #
    def at_pixel(self, pos, dfl_when_out, *, corner = None):
        corner = corner or self.corner
        pos = (pos[0] - corner[0], pos[1] - corner[1])
        if not (0 <= pos[0] < self.width) or not (0 <= pos[1] < self.height):
            return dfl_when_out or None
        return self._at_rel_pixel(pos)
    ###

def lerp(t, u, v):
    return (1 - t) * u + t * v 

_rainbow6 = np.array(
        [[255, 0, 0], [255, 255, 0], [0, 255, 0], [0, 255, 255], [0, 0, 255], [255, 0, 255]])

def v_rainbow01(t):
    q, r = int(t // (1 / 6)), t % (1 / 6)
    r *= 6
    return lerp(r, _rainbow6[q], _rainbow6[(q + 1) % 6])

def v_hsl(h01, s, l):
    white = np.array([255, 255, 255])
    black = np.array([0, 0, 0])
    #
    hue = v_rainbow01(h01)
    sat_hue = lerp(s, white, hue)
    return lerp(l, black, sat_hue)

