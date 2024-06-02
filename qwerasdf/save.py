import os
from pygame import Color

from .params import params
from .shape import *
from .util import naive_scan, Rec, sprint, clamp
from .merge import merge_weaves

class SaveError(BaseException): pass

def save_path(file):
    # note: `file` can be nested
    if file[-3:] != '.qw': file += '.qw'
    #
    prefixed = os.path.join(params.save_dir, file)
    os.makedirs(os.path.dirname(prefixed), exist_ok = True)
    return prefixed

def save_buffer(context, extra = set()): 
    def weave_data_line(we, ckey):
        shape_id1 = context.shapes.index(we.hangpoints[0].s)
        shape_id2 = context.shapes.index(we.hangpoints[1].s)
        line = f"{we.nwires} {we.incrs[0]} {we.incrs[1]} {ckey} "
        line += f"{shape_id1} {we.hangpoints[0].i} {shape_id2} {we.hangpoints[1].i}" 
        return line
    #
    context.weaves = merge_weaves(context.weaves + context.pending_weaves)
    lines = []
    def p(*a, **ka):
        lines.append(sprint(*a, **ka))
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
    if extra:
        p("EXTRADATA")
        for k in extra:
            line = f"{k}="
            try:
                match k: # only supported k = session for now
                    case 'session':
                        line += os.path.basename(context.autosaver.root)
                p(line)
            except: pass # just ignore problematic lines
    #
    return ''.join(lines)

_save_header = ''.join([
    "# shape format: id: type ndivs x1 y1 ...\n",
    "# weave format: n inc1 inc2 color_key shape_id1 i1 shape_id2 i2\n",
    "# color format: key r g b\n",
])
def write_save(filename, buffer, overwrite_ok = True, header = False):
    open_mode = 'w' if overwrite_ok else 'x'
    try:
        filename = os.path.join('.', filename)
        os.makedirs(os.path.dirname(filename), exist_ok = True)
        with open(filename, open_mode) as f:
            buffer = _save_header + buffer if header else buffer
            f.write(buffer)
    except (FileExistsError, OSError): raise
    except:
        os.remove(filename)
        raise

def save(filename, context, overwrite_ok = True, header = True, extra = {'session'}):
    buffer = save_buffer(context, extra)
    write_save(filename, buffer, overwrite_ok, header)

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
            extra = {}
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
                        case 'EXTRADATA':
                            [k, v] = line.strip().split('=')
                            extra[k] = v
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
                    pending_weaves = [], # needed for `save_buffer`
                    weave_colors = colors,
                    palette = palette)
            return loaded_subcontext, extra
    except ParseError: raise
    except: raise LoadError()

class Autosaver: # autosaves system
    class DirectoryBusyError(BaseException): pass
    #
    def __init__(self, root, pulse = 10):
        try: 
            os.makedirs(root, exist_ok = True)
            with open(os.path.join(root, '.busy'), 'x'): pass # touch .busy
        except FileExistsError: 
            raise Autosaver.DirectoryBusyError()
        #
        self.last_load = 0
        self.back, self.last_buffer = 0, ''
        self.root = root
        #
        self.pulse = pulse
        self.rotorctl = params.autosave_rotorctl
        try:
            with open(os.path.join(self.root, '.rotor')) as rotorfile:
                self.rotor = [int(w) for w in next(rotorfile).split()]
        except:
            self.rotor = [0] 
        #
        self.nsaves = 0
        try:
            dir = self.root
            while True:
                self.nsaves += len([ f for f in os.listdir(dir) 
                    if (f[0] != '.' and os.path.isfile(os.path.join(dir, f))) ])
                dir = os.path.join(dir, 'older')
        except FileNotFoundError:
            pass
    #
    def finish(self):
        with open(os.path.join(self.root, '.rotor'), 'w') as rotor:
            rotor.write(' '.join([str(i) for i in self.rotor]) + '\n')
        #
        try: os.remove(os.path.join(self.root, '.busy'))
        except: pass
    #
    def savepoint(self, context):
        # k = directory nesting depth
        def archive(k, destdir, src):
            if not (k < len(self.rotorctl)): return
            if not (k < len(self.rotor)):
                self.rotor.append(0)
            #
            isave = self.rotor[k]
            try: n, d = self.rotorctl[k]
            except: n, d = self.rotorctl[k], None
            #
            dest = os.path.join(destdir, str(isave))
            if not os.path.isfile(dest):
                self.nsaves += 1
            elif d and isave % d == 0:
                archive(k + 1, os.path.join(destdir, 'older'), dest)
            os.makedirs(destdir, exist_ok = True)
            if os.path.isfile(dest): os.remove(dest)
            os.rename(src, dest)
            self.rotor[k] = (isave + 1) % n
        ###
        buffer = save_buffer(context)
        if self.last_buffer == buffer:
            return
        self.last_buffer = buffer
        savename = os.path.join(self.root, 'tmp')
        write_save(savename, buffer)
        archive(0, self.root, savename)
        self.back = 0
    #
    def rewind(self, n = 1):
        if self.nsaves == 0: return
        self.back = clamp(self.back + n, 0, self.nsaves - 1) # number *back* in time
    #
    def unwind(self, n = 1):
        self.rewind(-n)
    #
    def current_file(self):
        if self.nsaves == 0: return
        #
        back, reldir = self.back, ''
        for k in range(len(self.rotorctl) - 1):
            try: n, _ = self.rotorctl[k]
            except: n = self.rotorctl[k]
            if back < n: 
                break
            #
            reldir = os.path.join(reldir, 'older')
            back -= n
            k += 1
        isave = (self.rotor[k] - (back + 1)) % n
        savename = os.path.join(self.root, reldir, str(isave))
        return savename
    #
    def load_current(self, context):
        if self.last_load == self.back: return
        #
        if load_me := self.current_file() : 
            loaded_data, _ = load(load_me)
            self.last_buffer = save_buffer(loaded_data)
            self.last_load = self.back
            return loaded_data
        else:
            return None

