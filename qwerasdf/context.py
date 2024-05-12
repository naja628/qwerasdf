import numpy as np
import os

from pygame import Surface, event

from .util import Rec
from .params import params
from .save import Autosaver, load
from .math_utils import *
from .shape import bounding_rect

# def snappy_get_point(context, pos):
#     cx = context
#     sq_rrad = cx.view.ptord(params.snap_radius) ** 2
#     point = cx.view.ptor(pos)
#     snappoint = point
#     shortest = sq_rrad + params.eps
#     candidates = []
#     for sh in cx.shapes:
#         rels = sh.divs - point
#         rels **= 2
#         [xs, ys] = np.split(rels, 2, axis = 1)
#         sqdists = xs + ys
#         i = np.argmin(sqdists)
#         if sqdists[i] < min(sq_rrad, shortest):
#             snappoint, shortest = sh.divs[i], sqdists[i]
#         if sqdist(snappoint, sh.divs[i]) < params.eps ** 2:
#             candidates.append(Rec(s = sh, i = i))
#     #filter candidates, they need to be equal to actual found
#     candidates = [ cd for cd in candidates 
#             if sqdist(cd.s.divs[cd.i], snappoint) < params.eps ** 2]
#     return np.copy(snappoint), candidates
# 

# TODO:
# the way we currently get snappy points for the grid is kinda dumb, bc we generate 
# all the points and iterate over them,
# whereas we could do complicated-ish arithmetic in O1 i think, (in a method of Grid)
def snappy_get_point(context, pos):
    cx = context
    sq_rrad = cx.view.ptord(params.snap_radius) ** 2
    point = cx.view.ptor(pos)
    snappoint = point
    shortest = sq_rrad + params.eps
    candidates = []
    def find_shortest(points):
        # if len(points) == 0 ... are shapes garantueed to have at least a div?
        rels = points - point
        rels **= 2
        [xs, ys] = np.split(rels, 2, axis = 1)
        sqdists = xs + ys
        i = np.argmin(sqdists)
        return i, sqdists[i]
    #
    for sh in cx.shapes:
        i, d = find_shortest(sh.divs)
        #
        if d < min(sq_rrad, shortest):
            snappoint, shortest = sh.divs[i], d 
        if sqdist(snappoint, sh.divs[i]) < params.eps ** 2:
            candidates.append(Rec(s = sh, i = i))
    #filter candidates, they need to be equal to actual found
    if cx.grid_on and len(cx.grid.points()) != 0:
        i, d = find_shortest(cx.grid.points())
        if d < min(sq_rrad, shortest):
            snappoint = cx.grid.points()[i] 
    #
    candidates = [ 
            cd for cd in candidates 
            if sqdist(cd.s.divs[cd.i], snappoint) < params.eps ** 2]
    return np.copy(snappoint), candidates

def resize_context(context, new_width):
    context.weave_layer = Surface(context.screen.get_size())
    redraw_weaves(context)
    context.text.set_width(new_width)
    context.color_picker.reset(new_width, new_width // 8, min_sat = params.min_pick_saturation)

# WEAVES
def create_weave(context, weave, color = None):
    context.pending_weaves.append(weave)
    context.weave_colors[weave] = (color or context.color_key)
#
def all_weaves(context):
    return context.weaves + context.pending_weaves
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

def set_hints(context, *hints):
    context.hints = list(hints)

def reset_hints(context):
    context.hints = []

def post_info(msg, context):
    context.text.write_section('info', [ line.strip() for line in msg.split('\n') ])
    # context.text.write_section('info', [ 'Info: ' + msg ])

def post_error(msg, context):
    context.text.write_section('error', [ 'Error: ' + msg ])

# Selection actions
def unweave_inside_selection(context, filter_to_del = None):
    cx = context
    keep_weaves = []
    for we in cx.weaves:
        sh1, sh2 = (hg.s for hg in we.hangpoints)
        if not (sh1 in cx.selected and sh2 in cx.selected):
            keep_weaves.append(we)
        if filter_to_del and not filter_to_del(we):
            keep_weaves.append(we)
    cx.weaves = keep_weaves
    redraw_weaves(cx)

def unweave_into_selection(context):
    cx = context
    keep_weaves = []
    for we in cx.weaves:
        sh1, sh2 = (hg.s for hg in we.hangpoints)
        if sh1 not in cx.selected and sh2 not in cx.selected:
            keep_weaves.append(we)
        else:
            del cx.weave_colors[we]
    cx.weaves = keep_weaves
    redraw_weaves(cx)

def delete_selection(context, hints = True):
    unweave_into_selection(context)
    context.shapes = [ sh for sh in context.shapes if not sh in context.selected ]
    context.selected = []
    if hints:
        reset_hints(context)

def reload_session(context, session_name):
    cx = context
    if cx.autosaver and session_name == os.path.basename(cx.autosaver.root):
        return 
    #
    if session_name == 'OFF':
        if cx.autosaver: cx.autosaver.finish()
        cx.autosaver = None
        return
    #
    try:
        new_saver = Autosaver(os.path.join(params.autosave_dir, session_name),
                              pulse = params.autosave_pulse)
        if cx.autosaver: cx.autosaver.finish()
        cx.autosaver = new_saver
    except Autosaver.DirectoryBusyError:
        post_error(f"'{session_name}' session already in use. ", cx)

def load_to_context(context, loaded, extra = {}):
    context.hints = []
    context.selected = []
    #
    context.update(loaded)
    for k, v in extra.items():
        match k: # only k = session supported now
            case 'session': 
                reload_session(context, v)
    #
    redraw_weaves(context)

def import_to_context(context, file):
    loaded, _ = load(file)
    stash_frame = Rec()
    stash_frame.update(loaded)
    context.stash.push_shapes(stash_frame.shapes, stash_frame)
    #

MENU_RESET = event.custom_type()
def reset_menu(context, path = None):
    context.dispatch.dispatch([event.Event(MENU_RESET, path = None)])

def toggle_grid(context):
    context.grid_on = not context.grid_on

def copy_weaves_inside(dest_shapes, src_shapes, weave_superset, context,
        create = True, return_colors = False):
    # context needed for colors
    new_weaves = []
    if return_colors: colors = {}
    for we in weave_superset:
        [s1, s2] = [ hg.s for hg in we.hangpoints]
        try: i1, i2 = src_shapes.index(s1), src_shapes.index(s2)
        except: continue
        #
        new = we.copy()
        new.hangpoints[0].s, new.hangpoints[1].s = dest_shapes[i1], dest_shapes[i2]
        if context: 
            if create: create_weave(context, new, context.weave_colors[we])
            if return_colors: colors[new] = context.weave_colors[we]
        new_weaves.append( new )
    #
    if return_colors: return new_weaves, colors 
    else: return new_weaves

def stash_selection(context):
    cx = context
    cx.stash.push_shapes(cx.selected, cx)

## IMAGES
def export_image_window(context, img_conf = None):
    scr, v = context.screen, context.view
    w, h = scr.get_size()
    corners = [v.ptor([0, h -1]), v.ptor( [w - 1, 0] )] # y inversion weirdness
    img_conf = img_conf or context.img_conf
    file = img_conf.save_image(corners, context)
    post_info(f"image successfully exported to '{file}'", context)

def export_image_whole(context, img_conf = None, margin = params.image_margin):
    corners = ar(bounding_rect(*context.shapes))
    [left, bottom], [right, top] = corners
    margin_x = margin / 2 * (right - left)
    margin_y = margin / 2 * (top - bottom)
    #
    corners[0] -= ar([margin_x, margin_y])
    corners[1] += ar([margin_x, margin_y])
    #
    img_conf = img_conf or context.img_conf
    file = img_conf.save_image(corners, context)
    post_info(f"image successfully exported to '{file}'", context)
