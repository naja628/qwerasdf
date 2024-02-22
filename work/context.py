import numpy as np
import os

from util import Rec, sqdist
from params import params
from pygame import Surface
from save import Autosaver, load

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

def post_info(msg, context):
    context.text.write_section('info', [ 'Info: ' + msg ])

def post_error(msg, context):
    context.text.write_section('error', [ 'Error: ' + msg ])

# Selection actions
def unweave_inside_selection(context):
    cx = context
    keep_weaves = []
    for we in cx.weaves:
        sh1, sh2 = (hg.s for hg in we.hangpoints)
        if sh1 not in cx.selected or sh2 not in cx.selected:
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

def delete_selection(context):
    unweave_into_selection(context)
    context.shapes = [ sh for sh in context.shapes if not sh in context.selected ]
    context.selected = []

def reload_session(context, session_name):
    cx = context
    if session_name == 'OFF':
        if cx.autosaver: cx.autosaver.finish()
        cx.autosaver = None
        return
    #
    new_saver = Autosaver(os.path.join(params.autosave_dir, session_name),
                          pulse = params.autosave_pulse)
    if cx.autosaver: cx.autosaver.finish()
    cx.autosaver = new_saver
    if session_name == 'OFF':
        cx.autosaver.finish()
        cx.autosaver = None
        return

def load_to_context(context, file, load_extra = set()):
    context.hints = []
    context.selected = []
    loaded, extra = load(file)
    #
    context.update(loaded)
    for k, v in extra.items():
        if not k in load_extra:
            continue
        match k: # only k = session supported now
            case 'session': 
                reload_session(context, v)
    #
    redraw_weaves(context)

def import_to_context(context, file):
    loaded, _ = load(file)
    context.shapes += loaded.shapes
    context.selected = loaded.shapes
    context.weaves += loaded.weaves
    context.weave_colors.update(loaded.weave_colors)
    #
    redraw_weaves(context)

