import os
from pygame import Color

import params
from shape import *
from util import naive_scan, Rec
from context import redraw_weaves

class SaveError(BaseException): pass

def save(filename, context, overwrite_ok = True):
    def weave_data_line(we, ckey):
        shape_id1 = context.shapes.index(we.hangpoints[0].s)
        shape_id2 = context.shapes.index(we.hangpoints[1].s)
        line = f"{we.nwires} {we.incrs[0]} {we.incrs[1]} {ckey} "
        line += f"{shape_id1} {we.hangpoints[0].i} {shape_id2} {we.hangpoints[1].i}" 
        return line
    #
    open_flags = 'w' if overwrite_ok else 'x'
    #
    try:
        with open(filename, open_flags) as f:
            def p(*args, **kwargs):
                kwargs['file'] = f
                print(*args, **kwargs)
            #
            p("# shape format: id: type ndivs x1 y1 ...")
            p("# weave format: n inc1 inc2 color_key shape_id1 i1 shape_id2 i2")
            p("# color format: key r g b")
            #
            p("SHAPEDATA")
            for (i, s) in enumerate(context.shapes):
                p(f"{i}:", repr(s))
            #
            p("COLORDATA")
            for k, color in context.palette.items():
                p(f"{k} {color.r} {color.g} {color.b}")
            #
            p("WEAVEDATA")
            for we in context.weaves:
                p(weave_data_line(we, context.weave_colors[we]))
            #
    except (FileExistsError, OSError): raise
    except:
        os.remove(filename)
        raise # TODO ??
        raise SaveError()
    ###

def save_path(file):
    # note: `file` can be nested
    if file[-3:] != '.qw': file += '.qw'
    #
    prefixed = os.path.join(params.save_dir, file)
    os.makedirs(os.path.dirname(prefixed), exist_ok = True)
    return prefixed

class LoadError(BaseException): pass
class ParseError(BaseException):
    def __init__(self, i, line, section = None):
        self.i, self.line, self.section = i, line, section
    #
    def __str__(self):
        return ' / '.join(self.format().split('\n'))
    #
    def format(self):
        msg = f"In section {self.section}" if self.section else "Missing Section Header"
        #msg = f"In section " + self.section if section else "Missing Section Header"
        fstr = f"ParseError on line {self.i}: {msg}\n"
        fstr += f"{self.i} | {self.line}\n"
        return fstr
    ###

def load(filename):
    try:
        with open(filename, 'r') as f:
            section = None
            sh_dict = {}
            palette = {}
            weave_lines = []
            for i, line in enumerate(f):
                try:
                    # ignore empty and comments
                    if line.strip() == '' or line.strip()[0] == '#': continue
                    # section header
                    if line[-5:-1] == 'DATA': section = line[:-1]; continue
                    #
                    match section:
                        case 'SHAPEDATA':
                            [shape_id, data] = line.split(':')
                            shape_id = int(shape_id)
                            sh_dict[shape_id] = create_shape_from_repr(data)
                        case 'COLORDATA':
                            key, r, g, b = naive_scan(line, None, int, int, int)
                            if len(key) != 1: raise Exception()
                            palette[key] = Color(r, g, b)
                        case 'WEAVEDATA':
                            weave_lines.append(line)
                        case _: raise Exception()
                except: 
                    raise ParseError(i + 1, line, section)
            ###
            weaves, colors = [], {}
            for i, line in enumerate(weave_lines):
                try:
                    convs = [int] * 8; convs[3] = None
                    n, inc1, inc2, ckey, id1, i1, id2, i2 = naive_scan(line, *convs)
                    hangs = [ Rec(s = sh_dict[idx], i = ix)  for idx, ix in ((id1, i1), (id2, i2)) ] 
                    we = Weave(hangs, n, (inc1, inc2))
                    weaves.append(we)
                    colors[we] = ckey
                except:
                    raise ParseError(i + 1, line, 'WEAVEDATA')
            ###
            loaded_subcontext = Rec(
                    shapes = list(sh_dict.values()), 
                    weaves = weaves,
                    weave_colors = colors,
                    palette = palette)
            return loaded_subcontext
    except ParseError: raise
    except: raise LoadError()

def load_to_context(file, context):
    context.hints = []
    context.selected = []
    #
    context.update(load(file))
    redraw_weaves(context)

## for custom events (probably in hooks
AUTOSAVE = pg.event.custom_event() 
pg.time.set_timer(AUTOSAVE, 10 * 1000)

#
