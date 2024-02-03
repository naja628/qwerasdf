import numpy as np

from util import Rec, sqdist
import params
from pygame import Surface

# def snappy_get_point(context, pos):
#     cx = context # shorter to write
#     rrad = cx.view.ptord(params.snap_radius)
#     shortest = rrad + params.eps
#     point = cx.view.ptor(pos)
#     candidates = []
#     for s in cx.shapes:
#         for i, div in enumerate(s.divs):
#             if (d := dist(div, cx.view.ptor(pos))) < min(rrad, shortest):
#                 shortest = d
#                 point = div
#             if dist(point, div) < params.eps:
#                 candidates.append(Rec(s = s, i = i))
#     # filter candidates
#     candidates = [ cd for cd in candidates 
#             if dist(cd.s.divs[cd.i], point) < params.eps ]
#     return point, candidates

def snappy_get_point(context, pos):
    cx = context
    sq_rrad = cx.view.ptord(params.snap_radius) ** 2
    point = cx.view.ptor(pos)
    snappoint = point
    shortest = sq_rrad + params.eps
    candidates = []
    for sh in cx.shapes:
        rels = sh.divs - point
        rels **= 2
        [xs, ys] = np.split(rels, 2, axis = 1)
        sqdists = xs + ys
        i = np.argmin(sqdists)
        if sqdists[i] < min(sq_rrad, shortest):
            snappoint, shortest = sh.divs[i], sqdists[i]
        if sqdist(snappoint, sh.divs[i]) < params.eps ** 2:
            candidates.append(Rec(s = sh, i = i))
    #filter candidates, they need to be equal to actual found
    candidates = [ cd for cd in candidates 
            if sqdist(cd.s.divs[cd.i], snappoint) < params.eps ** 2]
    return snappoint, candidates

def resize_context(context, new_width):
    context.weave_layer = Surface(context.screen.get_size())
    redraw_weaves(context)
    context.bottom_text.set_surface(new_width)
    context.menubox.set_surface(new_width)
    context.color_picker.reset(new_width, new_width // 8, min_sat = params.min_pick_saturation)

# WEAVES
def create_weave(context, weave, color = None):
    context.pending_weaves.append(weave)
    context.weave_colors[weave] = (color or context.color_key)
#
def redraw_weaves(context):
    context.redraw_weaves = True
#
def set_color(context, color_key, new_color):
    context.palette[color_key] = new_color
    context.redraw_weaves = True
#

def create_shapes(context, *shapes):
    context.shapes.extend(shapes)
    context.selected = list(shapes)
    # TODO automerge ? maybe only in selection

def set_hints(context, *hints):
    context.hints = list(hints)

def reset_hints(context):
    context.hints = []

# TEXT
def post_error(msg, context):
    context.bottom_text.set_line(context.ERRLINE, f"Error: {msg}", params.error_text_color)

def post_info(msg, context):
    context.bottom_text.set_line(context.INFOLINE, f"Error: {msg}", params.text_color)

