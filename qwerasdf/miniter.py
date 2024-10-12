from pygame import display, FULLSCREEN
from numpy import pi
import copy
import os
import re

from .params import params, ltop, ptol
from .util import Rec, param_decorator, eprint
from .save import *
from .context import *
from . import printpoints
from .math_utils import *
from .merge import merge_into
from .image import ImageConf

# set by `miniter_command` decorator
miniter_aliases_map = {} # cmd funs to aliases (ie command names)
miniter_usage_map = {} # cmd funs to usage messages
miniter_command_map = {} # aliases to cmd funs 

def miniter_exec(cmd, context):
    return term_exec(cmd, miniter_command_map, miniter_usage_map, context)
#
def term_exec(cmd, cmd_map, usage_map, context):
    if cmd.strip() == '':
        return 0
    #
    def parse_cmd(cmd):
        # maybe parse opts?
        # maybe allow some quoting 
        def naive_autocast(s):
            assert len(s) > 0 # ok bc comes from `split`
            if re.fullmatch(r'[+-]?[0-9]+', s):
                return int(s)
            elif re.fullmatch(r'[+-]?[0-9]+\.[0-9]*', s):
                return float(s)
            else:
                return s
        #
        def parse_kwarg(kwarg):
            split = kwarg.find('=')
            return kwarg[:split], naive_autocast(kwarg[split + 1:])
        #
        [cmd, *tokens] = cmd.split()
        args = [naive_autocast(tok) for tok in tokens if '=' not in tok]
        kwarg_list = [parse_kwarg(tok) for tok in tokens if '=' in tok]
        kwargs = { k : v for (k, v) in kwarg_list }
        kwargs['_env'] = Rec(context = context, cmd = cmd)
        return cmd, args, kwargs
    #
    try:
        cmd, args, kwargs = parse_cmd(cmd)
        if not cmd: return 0
        if not cmd in cmd_map:
            post_error("Command not found", context)
            return 1
        cmd_map[cmd](*args, **kwargs)
        return 0
    except CmdExn as e: 
        post_error(str(e), context); return e.exit_code
    except BaseException as e:
        try:
            eprint('debug info: term caught', type(e), e) # debug
            usage_msg = usage_map[cmd_map[cmd]].replace('$CMD', cmd)
            post_error(usage_msg, context)
        except BaseException as e:
            eprint('debug info: term REcaught', type(e), e) #debug
            post_error(str(e), context)
        return 1
 
class CmdExn(Exception): 
    def __init__(self, *a, exit_code = 1, **ka):
        self.exit_code = exit_code
        Exception.__init__(self, *a, *ka)

@param_decorator
def miniter_command(cmd_fun, aliases, usage = '$CMD'):
    global miniter_aliases_map, miniter_usage_map
    if type(aliases) is str : aliases = (aliases, )
    miniter_aliases_map[cmd_fun] = aliases
    miniter_usage_map[cmd_fun] = 'Usage: ' + usage
    miniter_command_map.update({ alias : cmd_fun for alias in aliases })
    return cmd_fun

############## CMDS (COMMANDS) ######################

# Any exception in a command -> show usage and "continue"
# Except CmdExn as e -> show `str(e)` (and "continue")
# This mean you should rethrow `CmdExn` for exceptions that are not necessarily the user's fault

# `_env` argument is needed (even if not used)
# better/safer to make it keyword-only (eg with `xx_cmd(..., *, _env)`)

## Help and Doc
def _slash_aliases(cmd_name):
    return '/'.join(miniter_aliases_map[miniter_command_map[cmd_name]])

@miniter_command(('help', 'h'), "$CMD CMD")
def help_cmd(cmd_name, *, _env):
    "$CMD CMD: show documentation for CMD"
    #
    post_info(f"{miniter_command_map[cmd_name].__doc__.replace('$CMD', cmd_name)}", _env.context)

def _fuzzy_matches(search, candidates):
    if search in candidates: # prioritize exact match
        return [ search ]
    #
    def is_match(cdt):
        i = 0
        for ch in search:
            try: i = cdt.index(ch, i) + 1
            except ValueError: return False 
        return True
    return filter(is_match, candidates)

@miniter_command(('ls-cmd', 'ls'), "$CMD || $CMD SEARCH")
def list_cmd(search = None, *, _env):
    '''$CMD: list available commands
       $CMD SEARCH: list commands matching SEARCH (by-name)'''
    #
    cmd_names = [ aliases[0] for aliases in miniter_aliases_map.values() ]
    if not search:
        post_info( ', '.join(cmd_names), _env.context )
    else:
        matches = [*_fuzzy_matches(search, cmd_names)]
        if matches: post_info( ', '.join(matches), _env.context )
        else: post_info( f"no match for '{search}'", _env.context )

@miniter_command(('usage', 'us'), "$CMD CMDNAME")
def usage_cmd(cmd_name, *, _env):
    "$CMD CMD: show command usage"
    #
    cmd_names = '/'.join(miniter_aliases_map[miniter_command_map[cmd_name]])
    usage_str = miniter_usage_map[miniter_command_map[cmd_name]]
    post_info(usage_str.replace('$CMD', cmd_names), _env.context)


## Quit and Save
def _saves_list(ext = False):
    def no_ext(f):
        i = f.rfind('.')
        return f[:i] if i > 0 else f
    if ext: return [*os.listdir(params.save_dir)]
    else: return [no_ext(f) for f in os.listdir(params.save_dir)]

def _cmp_buff(context):
    buffer = save_buffer(context, extra = {'session'})
    same = (context.last_save_buffer == buffer)
    return same, buffer

_last_save_filename = None
@miniter_command(('save', 's'), "$CMD SAVENAME || $CMD ! || $CMD SAVENAME !")
def save_cmd(*a, _env):
    '''$CMD SAVENAME ! : save as SAVENAME
       $CMD SAVENAME   : same as above but forbid overwriting existing save.
       $CMD !          : save (using the previous SAVENAME)'''
    #
    global _last_save_filename
    if not (1 <= len(a) <= 2): raise Exception()
    try:
        file = _last_save_filename if a == ('!',) else a[0]
        if file == None: 
            raise CmdExn("No previous savename")
        if file.find('..') >= 0 or file.find('/') >= 0:
            raise CmdExn("savenames can't contain '..' or '/'")
        overwrite_ok = (a[-1] == '!')
        #
        buffer = save_buffer(_env.context, extra = {'session'})
        write_save(save_path(file), buffer, overwrite_ok = overwrite_ok, header = True)
        post_info( f"successfully saved as '{file}'", _env.context )
        #
        _env.context.last_save_buffer = buffer
        _last_save_filename = file
    except FileExistsError:
        raise CmdExn(f"'{file}' exists. to allow overwrites, use: {_env.cmd} {file} !")

@miniter_command(('remove-save', 'rm'), "$CMD SAVE1 ...")
def remove_save(*names, _env):
    '''$CMD SAVE1 ...: delete saves'''
    for name in names:
        try: 
            os.remove(save_path(name))
            post_info(f"removed '{name}'", _env.context)
        except: pass

@miniter_command(('ls-saves', 'lsav'), "$CMD || $CMD SEARCH_TERM")
def ls_saves_cmd(search = None, *, _env):
    '''$CMD            : list all existing save names
       $CMD SEARCHTERM : list all existing save names matching the search
       Search Criterion: all letters appears in order. (eg 'ac' matches 'abc' but not 'ca')
       If the search term is a complete name, list only it (and not other matches)'''
    saves = _saves_list()
    if search:
        matches = [*_fuzzy_matches(search, saves)]
        if matches == []: post_info(f"no matches for '{search}'.", _env.context)
        else: post_info(f"matches for '{search}': {', '.join(matches)}", _env.context)
    else:
        post_info(', '.join(saves), _env.context) 

@miniter_command(('load', 'lo'), "$CMD SEARCHSAVE || $CMD SEARCHSAVE !")
def load_cmd(search_file, bang = None, *, _env):
    '''$CMD SEARCHSAVE ! : find matches for SEARCHSAVE according to 'ls-saves' rules, and load the save if a single match is found.
       $CMD SEARCHTERM   : same as above but forbids discarding unsaved changes'''
    #
    global _last_save_filename
    if bang != '!' and bang is not None: raise Exception()
    #
    same, _ = _cmp_buff(_env.context)
    if bang != '!' and not same:
        raise CmdExn(f"Would discard changes. Use '{_env.cmd} {search_file} !' to ignore")
    #
    try:
        matches = [*_fuzzy_matches(search_file, _saves_list())]
        if len(matches) == 0: raise CmdExn(f"no match for '{search_file}' found")
        elif len(matches) > 1: raise CmdExn(f"found several matches: {', '.join(matches)}")
        #
        load_file = save_path( matches[0] )
        loaded_data, extra = load(load_file)
        load_to_context(_env.context, loaded_data, extra)
        #
        _env.context.last_save_buffer = save_buffer(_env.context, extra = {'session'})
        _last_save_filename = matches[0]
        reset_menu(_env.context)
    except ParseError as e: raise CmdExn(str(e))
    except LoadError: raise CmdExn(f"Error loading {load}")

@miniter_command( ('exit', 'quit', 'q'), "$CMD || $CMD ! || $CMD SAVENAME")
def exit_cmd(save_or_bang = None, *, _env):
    '''$CMD   : quit program. forbids discarding unsaved changes.
       $CMD ! : quit program.
       $CMD SAVENAME: save as savename, then quit program.'''
    #
    cx = _env.context
    same, buffer = _cmp_buff(_env.context)
    if not save_or_bang and not same:
        raise CmdExn(f"Quitting would discard changes. Use '{_env.cmd} !' to ignore")
    #
    if save_or_bang and save_or_bang != '!':
        write_save(save_path(save_or_bang), buffer, header = True)
    _env.context.QUIT = True

@miniter_command(('new', 'blank'), "$CMD || $CMD ! || $CMD SAVENAME")
def new_design_cmd(save_or_bang = None, *, _env):
    '''$CMD   : clear canvas and start new drawing. forbids discarding unsaved changes.
       $CMD ! : clear canvas and start new drawing.
       $CMD SAVENAME: save as savename, then clear canvas and start new drawing.'''
    same, buffer = _cmp_buff(_env.context)
    if not save_or_bang and not same:
        raise CmdExn(f"Would discard changes. Use '{_env.cmd} !' or '{_env.cmd} savename'")
    if save_or_bang and save_or_bang != '!':
        write_save(save_path(save_or_bang), buffer, overwrite_ok = True, header = True)
    cx = _env.context
    cx.selected = []
    cx.shapes = []
    cx.hints = []
    cx.weaves = []
    cx.weave_colors = {}
    reset_menu(cx)
    _env.context.last_save_buffer = ''
    _last_save_filename = None
    redraw_weaves(cx)

@miniter_command(('import', 'imp'), "$CMD SAVENAME")
def import_cmd(search_save, *, _env):
    '''$CMD SAVENAME: load SAVENAME **on top** of the stash
       note: performs matching on the savename (cf load, ls-saves)'''
    matches = [*_fuzzy_matches(search_save, _saves_list())]
    match matches:
        case [ matched ]: 
            try:
                import_to_context(_env.context, save_path(matched))
            except ParseError as e: raise CmdExn(str(e))
            except LoadError: raise CmdExn(f"Error loading {file}")
        #
        case []: raise CmdExn(f"no match for '{search_save}' found")
        case matches: raise CmdExn(f"found several matches: {', '.join(matches)}")
    ###

@miniter_command(('recover',) )
def recover_cmd(*, _env):
    "$CMD: try to recover state from a previous crash"
    load_cmd(params.recover_filename, '!',  _env = _env)
    os.remove(save_path(params.recover_filename))
    post_info(f"recovery succesful: '{params.recover_filename}' has been deleted", _env.context)

@miniter_command(('outline', 'out'), "$CMD WIDTH_CM MARGIN_CM [PAPER_FORMAT]")
def export_outline_cmd(width, margin, paper = 'a4', *, _env):
    '''$CMD WIDTH_CM MARGIN_CM: generate multi-page printable outline for drawing.
       (cf. manual. (Saving section))'''
    us_letter = (paper.lower() == 'us-letter')
    points = np.concatenate([sh.divs for sh in _env.context.shapes])
    ps_buffer = printpoints.generate(points, width, margin, us_letter)
    file = os.path.join(params.exports_directory, 'out.ps')
    with open(file, 'w') as out:
        out.write(ps_buffer)
    post_info(f"outline written to '{file}'", _env.context)

@miniter_command(("image-height", "imh"), "$CMD HEIGHT")
def image_height_cmd(h, *, _env):
    "$CMD HEIGHT: set height in pixel of exported images"
    if not ( 8 <= h <= 17000 ):
        CmdExn("height must be between 8 and 17000")
    _env.context.img_conf.height = h

@miniter_command(("image-format", "image-extension", "ext"), "$CMD EXTENSION")
def image_extension_cmd(ext, *, _env):
    "$CMD EXTENSION: set format to use when exporting images"
    if ext not in {'png', 'jpeg', 'tga'}:
        raise CmdExn("Supported formats: png, jpeg, tga")
    _env.context.img_conf.extension = ext

@miniter_command(("export-image", "exp"), "$CMD win|all HEIGHT [FORMAT]")
def export_image_cmd(what = 'win', height = None, format = 'png', *, _env):
    '''$CMD win HEIGHT: export an HEIGHT pixels high png image of the window
       $CMD all HEIGHT: export an HEIGHT pixels high png image of the whole drawing
       $CMD ... FORMAT: same as above, but FORMAT is the image format (png, jpeg, tga)'''
    if what not in {'win', 'all'}: CmdExn("First argument must 'win' or 'all'")
    if format not in {'png', 'jpeg', 'tga'}: CmdExn("Unrecognized formatt. Supported formats: png, jpeg, tga")
    height = height or _env.context.screen.get_size()[1]
    if not ( 8 <= height <= 17000): CmdExn("height must be between 8 and 17000")
    img_conf = ImageConf(height, format, params.exports_directory)
    if what == 'win': export_image_window(_env.context, img_conf)
    elif what == 'all': export_image_whole(_env.context, img_conf)

## Set Params
@miniter_command(('set-color', 'co'), "$CMD KEY || $CMD KEY R G B || $CMD KEY HHHHHH")
def set_color_cmd(*args, _env):
    '''$CMD KEY       : select color KEY for drawing.
       $CMD KEY R G B : set color KEY by RGB
       $CMD KEY HHHHHH: set color KEY by hexcode'''
    #
    def set_rgb(r, g, b):
        set_color(_env.context, key, Color(r, g, b))
    #
    def set_hex(hexstr):
        hexstr = str(hexstr)
        if hexstr[:2].lower() == "0x":
            hexstr = hexstr[2:]
        hexstr = hexstr.rjust(6, '0')
        [r, g, b] = [int(hexstr[i:i+2], 16) for i in range(0, 6, 2)]
        set_rgb(r, g, b)
    #
    key = ltop(args[0].upper())
    if key not in _env.context.palette: raise CmdExn("Invalid color key")
    #
    match args[1:]:
        case []: _env.context.color_key = key
        case [hexcolor]: set_hex(hexcolor)
        case [r, g, b]: set_rgb(r, g, b)

@miniter_command(('menu',))
def show_menu_cmd(*, _env):
    "$CMD: show/hide menu"
    _env.context.show_menu = not _env.context.show_menu
    _env.context.text.write_section('menu', [])

@miniter_command( ('palette', 'pal') )
def show_palette_cmd(*, _env):
    "$CMD: show/hide palette"
    #
    _env.context.show_palette = not _env.context.show_palette

@miniter_command( ('div', 'nails', 'n'), "$CMD N   (N = new number of nails)")
def set_div_cmd(n, *, _env):
    "$CMD N: set the number of nails on all selected shapes to N. (evenly spaced)"
    #
    if not ( 0 < n <= params.max_div) :
        raise CmdExn(f"number must be between 1 and {params.max_div}")
    unweave_into_selection(_env.context)
    for sh in _env.context.selected:
        sh.set_divs(n)

@miniter_command( ('default-divs', 'dfdiv', 'dfnails'), "$CMD SHAPE_TYPE1 DEFAULT_NAILS1 ...")
def set_default_divs_cmd(*args, _env):
    '''$CMD SHAPE_TYPE1 DEFAULT_NAILS1 ...: all shapes of type SHAPE_TYPE1 will be initially drawn with DEFAULT_NAILS1 nails.
       Shape types: 'circle', 'line', 'arc', 'poly'
       Can specify several (type, dfnails) pairs at once (after each other).'''
    def bundle2(l):
        it = iter(l)
        try: yield (next(it), next(it))
        except: return
    #
    df_divs = _env.context.df_divs
    for ( shape_type, div ) in bundle2(args):
        div = int(div)
        if div < 1: raise Exception()
        if shape_type in df_divs:
            df_divs[shape_type] = div
        else:
            types_list = ', '.join( ( f"'{type}'" for type in df_divs.keys()) )
            post_error(f"acceptable shape types are: {types_list}", _env.context)

@miniter_command( ('weavity', 'wy'), "$CMD BOUND_INCREMENT LOOSE_INCREMENT")
def set_weavity_cmd(inc0 = 1, inc1 = 1, *, _env):
    "$CMD BOUND_INCREMENT LOOSE_INCREMENT: set the weavity pair. (cf Weaves section of manual)"
    #
    if inc1 <= 0:
        raise CmdExn("2nd weavity number must be positive (non-zero)")
    _env.context.weavity = (inc0, inc1)

@miniter_command( ('weaveback', 'wb') )
def toggle_weaveback(*, _env):
    "$CMD: toggle weaveback"
    _env.context.weaveback = not _env.context.weaveback

def _read_angle(*a):
    n = len(a)
    if n == 1: return a[0] * pi / 180
    if n == 2 and a[1].to_lower() == 'pi': return a[0] * pi
    if n == 3 and a[1] == '/': return a[0] / a[2] * 2 * pi
    raise Exception()

@miniter_command(('set-rotation', 'rot'), "$CMD new_angle OR $CMD p / q  (p qth of a turn)")
def set_default_rotation_cmd(*a, _env):
    '''$CMD DEG   : set the default rotation angle to DEG degrees
       $CMD RAD pi: set the default rotation angle to RAD * pi radians. (literally type 'pi')
       $CMD P / Q : set the default rotation to P Qth of a turn. (spaces around the slash mandatory)'''
    _env.context.default_rotation = _read_angle(*a)

# Resizing
@miniter_command( ('fullscreen', 'fu') )
def fullscreen_cmd(*, _env):
    "$CMD: go fullscreen"
    #
    _env.context.screen = display.set_mode(flags = FULLSCREEN)
    resize_context(_env.context, _env.context.screen.get_width())

@miniter_command( ('resize', 'res'), "$CMD WIDTH HEIGHT")
def resize_cmd(w = params.start_dimensions[0], h = params.start_dimensions[1], *, _env):
    "$CMD WIDTH HEIGHT: resize window"
    #
    if w < 300 or h < 300 or w > 5000 or h > 5000:
        raise CmdExn("bad dimensions")
    _env.context.screen = display.set_mode((w, h))
    resize_context(_env.context, w)


## Grid
@miniter_command(('grid',))
def grid_cmd(*, _env):
    "$CMD: enable/disable grid"
    toggle_grid(_env.context)

def _parse_subdiv(*a):
    a = [*a]
    try:
        i, _ = next( filter( lambda i_a: (i_a[1] == ':') , enumerate(a)) )
    except StopIteration:
        i = len(a)
    def validate(x):
        return (type(x) is int and x > 1)
    no_repeat, repeat = a[:i], a[i+1:]
    if not all( validate(x) for x in no_repeat + repeat ):
        raise Exception()
    return a[:i], a[i+1:]

@miniter_command(('grid-rsubdiv', 'grsub'), "$CMD DIV1 ... : REPEAT1 ...")
def grid_rsubdiv_cmd(*divs, _env):
    '''$CMD DIV1 ... : REPEAT1 ... -> set the 'radial subdivison' of the grid. 
       $CMD N -> divide the central circle into N rings
       $CMD N M -> subdivide each ring further into M subrings
       ...'''
    _env.context.grid.rsubdivs = _parse_subdiv(*divs)

@miniter_command(('grid-asubdiv', 'gasub'), "$CMD DIV1 ... : REPEAT1 ...")
def grid_asubdiv_cmd(*divs, _env):
    '''$CMD DIV1 ... : REPEAT1 ...-> set the 'angular subdivison' of the grid. 
       $CMD N -> divide the canvas into N equal angle subsectors
       $CMD N M -> divide each of the above sectors further into M subsectors
       ...'''
    _env.context.grid.asubdivs = _parse_subdiv(*divs)

@miniter_command(('set-phase', 'phase', 'ph'), "$CMD new_phase")
def set_phase_cmd(*a, _env):
    '''$CMD DEG   : set the grid phase to DEG degrees
       $CMD RAD pi: set the grid phase to RAD * pi radians. (literally type 'pi')
       $CMD P / Q : set the grid phase to P Qth of a turn. (spaces around the slash mandatory)'''
    ph = _read_angle(*a)
    _env.context.grid.phase = ph

## Drawing Config
@miniter_command(('antialias', 'aa'))
def antialias_cmd(*, _env):
    "$CMD: toggle antialasing for drawing weave strings"
    _env.context.antialias = not _env.context.antialias
    redraw_weaves(_env.context)

@miniter_command(('draw-width', 'width'), '$CMD WIDTH')
def draw_width_cmd(width, *, _env):
    "$CMD WIDTH: set width (in pixels) for drawing weave strings"
    if width < 1: raise Exception()
    _env.context.draw_width = int(width)
    redraw_weaves(_env.context)

@miniter_command(('show-hide', 'shi'), '$CMD THING_TO_HIDE1 ...')
def show_hide_cmd(*a, _env):
    "$CMD THING1 ...: show/hide certains types of elements (shapes, weaves, nails)"
    for cat in a:
        if cat not in {'weaves', 'shapes', 'nails'}:
            raise CmdExn("Recognized terms: weaves, shapes, nails")
        else:
            hide_set = _env.context.hide
            if cat in hide_set: hide_set.remove(cat)
            else: hide_set.add(cat)

## Misc
@miniter_command(('stash-capacity', 'stashcap'), "$CMD CAPACITY")
def set_stash_cap_cmp(new_cap, * _env):
    "$CMD CAPACITY: set stash capacity (ie max number of stashed items)"
    if type(new_cap) != int or new_cap < 0: raise Exception()
    #
    _env.context.stash.cap.set_cap(new_cap)

@miniter_command(('session', 'se'), "$CMD SESSIONNAME | $CMD OFF")
def connect_session_cmd(session_name = None, *,  _env):
    '''$CMD            : tell current session.
       $CMD SESSIONNAME: connect to session SESSIONNAME.
       $CMD OFF        : disable undoing/autosaving. (literally type 'OFF' as the SESSIONNAME)'''
    cx = _env.context
    if not session_name:
        if not cx.autosaver:
            post_info("no current session", cx)
        else:
            post_info(f"session: {os.path.basename(cx.autosaver.root)}", cx)
        return
    #
    try:
        reload_session(cx, session_name)
        if session_name == 'OFF':
            post_info("successfully disconnected", cx)
        else:
            post_info(f"'{session_name}' successfully connected", cx)
    except Autosaver.DirectoryBusyError:
        post_error("already in use.", cx)

@miniter_command(('clear', 'cl'))
def clear_cmd(*, _env):
    "$CMD: clear error/info messages"
    for section in {'info', 'error'}:
        _env.context.text.write_section(section, [])

@miniter_command(('select-all', 'sel*'))
def select_all_cmd(*, _env):
    "$CMD: select all shapes"
    _env.context.selected = _env.context.shapes[:]

def _translate_colors(src, dest, weaves, selected, cx):
    src, dest = (''.join(ltop(k) for k in ks) for ks in (src.upper(), dest.upper()))
    for i, we in enumerate(weaves):
        [s1, s2] = [hg.s for hg in we.hangpoints]
        if not (s1 in selected and s2 in selected):
            continue
        #
        try:
            key_index = src.index(cx.weave_colors[we])
            if (color := dest[key_index]) in cx.palette:
                cx.weave_colors[we] = dest[key_index]
        except: pass

@miniter_command(('translate-colors', 'trans'), "$CMD FROM TO  (example: $CMD qw az)")
def translate_colors_cmd(src, dest, *, _env):
    '''$CMD FROM TO: change the colors of the weaves inside the selection according to conversion rule
       ex: if FROM = Q and TO = A, weaves with color Q will turn to color A'''
    cx = _env.context
    _translate_colors(src, dest, cx.weaves, cx.selected, cx)
    redraw_weaves(_env.context)

@miniter_command(('unweave-color', 'unco'), "$CMD COLORKEYS")
def unweave_colors_cmd(*colorkeys, _env):
    "$CMD COLORKEYS: remove all weaves of a color in colorkeys inside the selection"
    cx = _env.context
    for k in ''.join(colorkeys).upper():
        if k in cx.palette:
            unweave_inside_selection(cx, lambda we: cx.weave_colors[we] == ltop(k))

@miniter_command(('raise'), "$CMD COLORKEYS")
def raise_colors_cmd(*colorkeys, _env):
    '''$CMD COLORS: raise weaves inside the selection of certain colors on top
       (last on top)'''
    cx = _env.context
    weaves = all_weaves(cx)
    ks = ''.join(colorkeys).upper()
    ks = ''.join([ltop(k) for k in ks])
    weaves_by_color = {**{k: [] for k in ks}, '_':[]}
    for we in weaves:
        s1, s2 = (hg.s for hg in we.hangpoints)
        if (
            s1 in cx.selected and s2 in cx.selected 
            and (k := cx.weave_colors[we]) in weaves_by_color
        ):
            weaves_by_color[k].append(we)
        else:
            weaves_by_color['_'].append(we)
    cx.weaves = []
    for k in '_' + ks:
        cx.weaves.extend(weaves_by_color[k])
    redraw_weaves(cx)

@miniter_command(('symmetrize', 'sym'), "$CMD PATTERN? COLORSFROM? COLORSTO?")
def symmetrize_cmd(*a, _env):
    '''$CMD PATTERN COLORSFROM COLORSTO: complete a circle around the grid, making rotated copies of the selection
       example of patterns: r, r1 (same as r), r2, s, s3, 2 (same as r2), (nothing) (same as r1)...
       rn: create copies by rotating by n * the grid sector angle
       sn: same as rn, but make an horizontally mirrored copy before rotating
       if COLORSFROM and COLORSTO are specified, change colors as if by translate-colors after every transform'''
    cx = _env.context
    if not _env.context.grid_on: raise CmdExn("Grid must be activated")
    #
    pattern, src, dest = '', '', ''
    match a:
        case (): pass
        case _pattern,  : pattern = str(_pattern)
        case _src, _dest: src, dest = _src, _dest
        case _pattern, _src, _dest: pattern, src, dest = _pattern, _src, _dest
        case _: raise Exception()
    #
    try: rs, k = re.fullmatch('([sSrR]?)([0-9]*)', pattern).groups()
    except: CmdExn("Bad symmetry pattern")
    rs, k = (rs.lower() or 'r'), int(k) if k else 1
    #
    # if s: mirror (hz) once, square colors permutation
    if rs == 's':
        mat = mirror_matrix(float(cx.grid.phase))
        new_shapes = [ sh.transformed(mat, cx.grid.center) for sh in cx.selected ]
        new_weaves = copy_weaves_inside(
                new_shapes, cx.selected, all_weaves(cx), cx)
        cx.shapes, new_shapes = merge_into(cx.shapes, new_shapes, new_weaves)
        #
        _translate_colors(src, dest, all_weaves(cx), new_shapes, cx)
        cx.selected += new_shapes
        #
        colormap = { x: y for x, y in zip(src, dest) }
        dest = ''.join([ colormap.get(k, k) for k in dest])
    # for r: rotate, apply color translation
    n = cx.grid.asubdiv(0)
    touched = [*cx.selected]
    rot = rot_matrix( tau / n * k )
    i = 1
    while (i * k % n != 0):
        i += 1
        new_shapes = [ sh.transformed(rot, cx.grid.center) for sh in cx.selected ]
        new_weaves = copy_weaves_inside(
                new_shapes, cx.selected, all_weaves(cx), cx)
        # ^^ possible optimisation, pass previous new_weaves
        cx.shapes, cx.selected = merge_into(cx.shapes, new_shapes, new_weaves)
        #
        touched.extend(cx.selected)
        #
        _translate_colors(src, dest, all_weaves(cx), cx.selected, cx)
    #
    cx.selected = touched
    redraw_weaves(cx)

@miniter_command(('highlight', 'hi'), "$CMD INDEX1 ...")
def highlight_cmd(index, *more, _env):
    "$CMD INDEX1 ...: highlight the nails at the specified indices on all selected shapes"
    cx = _env.context
    cx.hints = []
    for sh in cx.selected: 
        cx.hints.extend([
            Point(sh.get_div(i)) 
            for i in [index, *more] if sh.get_div(i) is not None
            ])
    ###

@miniter_command(('source', 'so' ), "$CMD CMDSFILE")
def source_cmd(file, *, _env):
    "$CMD CMDSFILE: read CMDSFILE, and execute its lines as commands"
    try:
        with open(file) as rc:
            for i, line in enumerate(rc):
                try:
                    if line.strip() == '' or line.strip()[0] == '#': continue
                    miniter_exec(line, _env.context)
                except:
                    raise CmdExn(f"line {i + 1} | {line}")
    except: 
        raise CmdExn(f"Error reading {file}")

@miniter_command(('oneshot-commands', 'one'))
def toggle_oneshot_cmd(*, _env):
    '''$CMD: toggle oneshot commands. (default: enabled)
       when enabled: the commandline closes after every command'''
    _env.context.oneshot_commands = not _env.context.oneshot_commands 

@miniter_command(('not-in-use',), "$CMD SESSIONNAME")
def not_in_use_command(session = 'default', *, _env):
    '''$CMD SESSION: Allow later connection to SESSION in spite of the "not in use" error.
       $CMD: same as: $CMD default
       Note that if SESSION is actually in use, this will badly mangle your undo history'''
    try:
        os.remove(os.path.join(params.autosave_dir, session, '.busy'))
        _env.context.text.write_section('error', []) # clear last error message
    except FileNotFoundError: pass

# Debug
@miniter_command(('_debug', '_db'))
def debug(*, _env):
    "$CMD: go into python debugger"
    cx = _env.context
    breakpoint()

# Not used in program itself but belongs here kinda
def _generate_markdown_doc():
    links = []
    for cmd, aliases in miniter_aliases_map.items():
        name = aliases[0]
        links.append( f"[{name}](#{name})" )
        doc = cmd.__doc__.replace('$CMD', name)
        doc = '\n'.join([line.strip() for line in doc.split('\n')])
        text = '\n'.join([
            f"### {name}",
            f"aliases: " + '/'.join([f'`{alias}`' for alias in aliases]),
            f"```\n{doc}\n```",
        ])
        print(text)
        print('')
    print(', '.join(links))

