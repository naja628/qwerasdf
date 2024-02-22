import os.path
from pygame import Color

from util import Rec, eprint
params = Rec()

#############################
params.start_dimensions = (800, 800)

params.save_dir = './save'
params.recover_filename = 'RECOVER.qw'
params.autosave_dir = './autosave'
#dotrc = os.path.expanduser('~/.qwerasdfrc')
params.dotrc_path = ['.qwerasdfrc', os.path.expanduser('~/.qwerasdfrc')]

params.background = Color(0, 0, 0)
# shape_color = Color(0, 128, 128)
params.shape_color = Color(32, 64, 64)
params.hint_color = Color(128, 32, 96)
params.select_color = Color(64, 0, 192)

params.point_radius = 1
params.div_color = Color(128, 128, 128)

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
params.error_text_color = Color(128, 32, 32)
params.term_color = Color(0, 160, 128)

params.term_xx_close = True # typing 'xx' or 'XX' at the end of the prompt will close the terminal

params.start_ndivs = 60 # TODO used anywhere?
params.snap_radius = 9

params.zoom_factor = 1.1

params.brightness_scroll_speed = 0.025
params.min_pick_saturation = 0.2

params.bottom_margin = 15

# touch at own risk
params.eps = 0.0000001 # distance under which two points are considered "the same"
params.max_div = 1000
params.max_ppu = 1e6
params.min_ppu = 1e-5

params.autosave_pulse = 2
params.autosave_rotorctl = [ (30, 3) ] * 5 + [ 30 ]

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
            xassert(s[0] == '#')
            [r, g, b] = [int(s[i:i+2], 16) for i in range(0, 6, 2)]
        except:
            raise CastExn("color (r, g, b or #xxxxxx)")
    return Color(r, g, b)

@cast
def rfloat(s, min = 1e-6, max = 1e6):
    try:
        x = int(s)
        xassert( min <= x <= max )
        return x
    except:
        raise CastExn("{min} <= float <= {max}")

def _read_conf():
    setable_to_type = {
            'background': rcolor(),
            #
            'shape_color': rcolor(),
            'select_color': rcolor(),
            'hint_color': rcolor(),
            #
            'point_color': rcolor(),
            'point_radius': rint(1, 4),
            #
            'zoom_factor': rfloat(0.25, 4),
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
            'bottom_margin': rint(0, 50)
            }
    #
    home = os.path.expanduser('~')
    allowed_names = ['qwerasdf.conf', '.qwerasdf.conf']
    for filename in [*allowed_names, *[os.path.join(home, f) for f in allowed_names]]:
        try: 
            f = open(filename)
            break
        except:
            continue
    else: 
        eprint("no conf file found")
        return
        ###
    try:
        for i, line in enumerate(f):
            if line.strip()[0] == '#': continue
            #
            [param, val_str] = [s.strip() for s in line.split('=')]
            try: 
                apply_cast = setable_to_type[param]
                val = apply_cast(val_str)
                setattr(params, param, val)
            except KeyError:
                eprint(f"line {i} | no such param: '{param}'")
            except BaseException as e:
                eprint(f"line {i} | expected [{e}] for '{param}', but got '{val_str}'")
    finally:
        f.close()
    ##
    
_read_conf() # read conf when initing module

