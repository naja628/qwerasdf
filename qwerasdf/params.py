import os.path
from pygame import Color

from .util import Rec, eprint
params = Rec()

#############################
params.start_dimensions = (800, 800)

_INSTALL = os.path.expanduser('~/.qwerasdf')
params.homedir = _INSTALL
params.save_dir = os.path.join(_INSTALL, 'save')
params.recover_filename = '_RECOVER_'
params.autosave_dir = os.path.join(_INSTALL, 'autosave')
params.dotrc_path = [os.path.expanduser('~/.qwerasdfrc'), '.qwerasdfrc']
params.exports_directory = os.path.realpath('.')

params.background = Color(0, 0, 0)
params.shape_color = Color(32, 64, 64)
params.hint_color = Color(128, 32, 96)
params.select_color = Color(90, 90, 255)

params.div_color = Color(128, 128, 128)
params.point_radius = 1
params.point_shape_radius = 2


params.start_palette = {
 'Q': Color(192, 32, 96),
 'W': Color(11, 153, 20),
 'E': Color(64, 0, 192),
 'R': Color(192, 128, 0),
 #
 'A': Color(160, 200, 128),
 'S': Color(0, 200, 100),
 'D': Color(192, 96, 32),
 'F': Color(100, 0, 200),
 }

params.font_size = 15
params.text_color = Color(192, 192, 192)
params.error_text_color = Color(200, 30, 60)
params.term_color = Color(0, 160, 128)

params.snap_radius = 9

params.zoom_factor = 1.1

params.brightness_scroll_speed = 0.025
params.min_pick_saturation = 0.2

params.bottom_margin = 15

params.grid_color = Color(150, 150, 150)
params.grid_fade_factor = 1 / 2
params.grid_sparseness_scroll_speed = 3

params.menu_translate = ('', '')
def _assoc(src, dest, k):
    i = src.find(k)
    if i < 0 or i >= len(dest): return k
    else: return dest[i]

def ptol(k): # position (scancode) to layout
    src, dest = params.menu_translate
    return _assoc(src, dest, k)

def ltop(k):
    dest, src = params.menu_translate
    return _assoc(src, dest, k)

params.eps = 0.00000003 # distance under which two points are considered "the same"
params.max_div = 1000
params.max_ppu = 3e5
params.min_ppu = 1

params.image_margin = 0.05

params.autosave_pulse = 2
params.autosave_rotorctl = [ (30, 3) ] * 5 + [ 30 ]

params.initial_stash_cap = 8
### CODE to read from conf

def cast(f):
    def partial(*a, **ka):
        return lambda s: f(s.strip(), *a, **ka)
    return partial

class CastExn(BaseException): pass

def xassert(truthy):
    if not truthy:
        raise CastExn

@cast
def rint(s, min = None, max = None):
    expected = "int"
    if min is not None: expected = f'{min} <= ' + expected
    if max is not None: expected += f' <= {max}'
    try:
        x = int(s)
        if min is not None: xassert( min <= x)
        if max is not None: xassert( x <= max)
        return x
    except:
        raise CastExn(expected)

@cast
def rcolor(s):
    def trans(s, tab):
        return ''.join([ tab.get(c, c) for c in s])
    try:
        words = filter(None, trans(s, {',': ' '}).split())
        [r, g, b] = [ rint(0, 255)(compo) for compo in words ]
    except:
        try:
            xassert(len(s) == 6)
            [r, g, b] = [int(s[i:i+2], 16) for i in range(0, 6, 2)]
        except:
            raise CastExn("color (r, g, b or xxxxxx (x = hex digit))")
    return Color(r, g, b)

@cast
def rfloat(s, min = 1e-6, max = 1e6):
    try:
        x = int(s)
        xassert( min <= x <= max )
        return x
    except:
        raise CastExn("{min} <= float <= {max}")

@cast
def rkeymap(s):
    try:
        [src, dest] = s.split(' ')
        return (src.upper(), dest.upper())
    except:
        CastExn("keymap (FROM TO)")

@cast
def rpath(s):
    return os.path.expanduser(s)

def _read_conf():
    setable_to_type = {
            'exports_directory': rpath(),
            #
            'background': rcolor(),
            #
            'shape_color': rcolor(),
            'select_color': rcolor(),
            'hint_color': rcolor(),
            #
            'grid_color': rcolor(),
            'grid_fade_factor': rfloat(0.01, 0.99),
            'grid_sparseness_scroll_speed': rint(1, 25),
            #
            'point_color': rcolor(),
            'point_radius': rint(0, 5),
            'point_shape_radius': rint(1, 10),
            #
            'zoom_factor': rfloat(1.01, 4),
            'brightness_scroll_speed': rfloat(1 / 256, 0.2),
            'min_pick_saturation': rfloat(0, 0.99),
            #
            'font_size': rint(5, 30),
            'text_color': rcolor(),
            'error_text_color': rcolor(),
            'term_color': rcolor(),
            #
            'snap_radius': rint(1, 100),
            #
            'bottom_margin': rint(0, 50),
            'image_margin': rfloat(0, 0.99),
            #
            'menu_translate': rkeymap()
            }
    #
    if not os.path.isdir(_INSTALL):
        return
    #
    for fname in os.listdir(_INSTALL): 
        if not (parts := fname.split('.')) or parts[-1] != 'conf':
            continue
        try:
            f = open(os.path.join(_INSTALL, fname))
            for i, line in enumerate(f):
                line = line.strip()
                if not line or line.strip()[0] == '#': continue
                #
                [param, val_str] = [s.strip() for s in line.split('=')]
                try: 
                    apply_cast = setable_to_type[param]
                    val = apply_cast(val_str)
                    setattr(params, param, val)
                except KeyError:
                    eprint(f"line {i+1} | no such param: '{param}'")
                except CastExn as e:
                    eprint(f"line {i+1} | expected [{e}] for '{param}', but got '{val_str}'")
                except:
                    eprint("Unexpected error reading conf")
        finally:
            f.close()
    ##
    
_read_conf() # read conf when initing module

