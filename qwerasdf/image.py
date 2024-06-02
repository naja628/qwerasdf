import pygame as pg
import math
from os import path

from .params import params
from .view import View

def draw(surf, view, context):
    cx = context
    if 'weaves' not in cx.hide:
        for we in cx.weaves: 
            ckey = cx.weave_colors[we]
            we.draw(surf, view, color = cx.palette[ckey], antialias = cx.antialias, width = cx.draw_width)
    #
    if 'shapes' not in cx.hide:
        for sh in cx.shapes:
            sh.draw(surf, view, params.shape_color, draw_divs = False)
    #
    if 'nails' not in cx.hide:
        for sh in cx.shapes:
            sh.draw_divs(surf, view)

def fit(pix_height, rcorners):
    [rleft, rbottom] = rcorners[0]
    [rright, rtop] = rcorners[1]
    view = View([rleft,rtop])
    view.ppu = pix_height // (rtop - rbottom)
    pix_width = int(math.ceil( (rright - rleft) / (rtop - rbottom) * pix_height ))
    surf = pg.Surface((pix_width, pix_height))
    return surf, view

def make_image(context, pix_height, corners):
    surf, view = fit(pix_height, corners)
    cx = context
    draw(surf, view, context)
    return surf

def _numbered_filename(dir, base, ext):
    def name(i):
        return path.join(dir, f"{base}{i}.{ext}")
    i = 0
    while path.exists(name(i)):
        i += 1
    return name(i)

class ImageConf:
    def __init__(self, height, extension, directory):
        self.height = height
        self.extension = extension
        self.directory = directory
        self.out_base = 'qw' # TODO make param?
    #
    def filename(self):
        return _numbered_filename(self.directory, self.out_base, self.extension)
    #
    def save_image(self, corners, context):
        surf = make_image(context, self.height, corners)
        file = self.filename()
        pg.image.save(surf, file)
        return file
