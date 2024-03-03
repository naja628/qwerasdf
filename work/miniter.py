from pygame import display, FULLSCREEN
from numpy import pi
import os

from params import params
from util import Rec, param_decorator, eprint
from save import *
from context import *
import printpoints 

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
            if s[0] == '-' or '0' <= s[0] <= '9':
                if '.' in s:
                    return float(s)
                else:
                    return int(s)
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

@miniter_command(('help', 'h'), "$CMD cmd_name")
def help_cmd(cmd_name, *, _env):
    "get description of command"
    #
    post_info(f"{_slash_aliases(cmd_name)}: {miniter_command_map[cmd_name].__doc__}", _env.context)

@miniter_command(('ls-cmd', 'ls'))
def list_cmd(*, _env):
    "list available commands"
    #
    post_info( ', '.join([ aliases[0] for aliases in miniter_aliases_map.values() ]), _env.context )

@miniter_command(('usage', 'us'), "$CMD cmd_name")
def usage_cmd(cmd_name, *, _env):
    "show command usage"
    #
    cmd_names = '/'.join(miniter_aliases_map[miniter_command_map[cmd_name]])
    usage_str = miniter_usage_map[miniter_command_map[cmd_name]]
    post_info(usage_str.replace('$CMD', cmd_names), _env.context)


## Quit and Save
def _fuzzy_matches(search, candidates):
    if search in candidates: # prioritize exact match
        return [ search ]
    #
    def is_match(cdt):
        i = 0
        for ch in search:
            try: i = cdt.index(ch, i)
            except ValueError: return False 
        return True
    return filter(is_match, candidates)

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
@miniter_command(('save', 's'), "$CMD file || $CMD ! || $CMD file !")
def save_cmd(*a, _env):
    "save. with ! : overwrite previous save"
    #
    global _last_save_filename
    if not (1 <= len(a) <= 2): raise Exception()
    try:
        file = _last_save_filename if a == ('!',) else a[0]
        if file == None: raise CmdExn("No previous savename")
        overwrite_ok = (a[-1] == '!')
        #
        buffer = save_buffer(_env.context, extra = {'session'})
        write_save(save_path(file), buffer, overwrite_ok = overwrite_ok, header = True)
        #
        _env.context.last_save_buffer = buffer
        _last_save_filename = file
    except FileExistsError:
        raise CmdExn(f"'{file}' exists. to allow overwrites, use: {_env.cmd} ! {file}")

@miniter_command(('ls-save', 'lsav'), "$CMD || $CMD search")
def ls_saves_cmd(search = None, *, _env):
    "show list of existing saves in default save directory, matching `search` if specified"
    saves = _saves_list()
    if search:
        matches = [*_fuzzy_matches(search, saves)]
        if matches == []: post_info(f"no matches for '{search}'.", _env.context)
        else: post_info(f"matches for '{search}': {', '.join(matches)}", _env.context)
    else:
        post_info(', '.join(saves), _env.context) 

@miniter_command(('load', 'lo'), "$CMD load_file || $CMD load_file !")
def load_cmd(load, bang = None, *, _env):
    "load file. Use ! to suppress save warning"
    #
    if bang != '!' and bang is not None: raise Exception()
    #
    same, _ = _cmp_buff(_env.context)
    if bang != '!' and not same:
        raise CmdExn(f"Would discard changes. Use '{_env.cmd} {load} !' to ignore")
    #
    try:
        matches = [*_fuzzy_matches(load, _saves_list())]
        if len(matches) == 0: raise CmdExn(f"no match for '{load}' found")
        elif len(matches) > 1: raise CmdExn(f"found several matches: {', '.join(matches)}")
        #
        [load] = matches
        load_to_context(_env.context, save_path(load), load_extra = {'session'})
#         _env.context.menu.go_path('')
        reset_menu(_env.context)
    except ParseError as e: raise CmdExn(str(e))
    except LoadError: raise CmdExn(f"Error loading {load}")

@miniter_command( ('exit', 'quit', 'q'), "$CMD save_to OR $CMD !")
def exit_cmd(save_or_bang = None, *, _env):
    "save and exit. use ! instead of save-name to skip saving"
    #
    cx = _env.context
    same, buffer = _cmp_buff(_env.context)
    if not save_or_bang and not same:
        raise CmdExn(f"Quitting would discard changes. Use '{_env.cmd} !' to ignore")
    #
    if save_or_bang != '!':
        write_save(save_path(save_or_bang), buffer, header = True)
    _env.context.QUIT = True

@miniter_command(('new', 'blank'), "$CMD || $CMD save_to || $CMD !")
def new_design_cmd(save_or_bang = None, *, _env):
    "save current project to 'save_to' (! to discard). and open a new blank design"
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
#     cx.menu.go_path('')
    redraw_weaves(cx)

@miniter_command(('import', 'imp'), "$CMD import_file ")
def import_cmd(file, *, _env):
    try:
        import_to_context(_env.context, save_path(file))
    except ParseError as e: raise CmdExn(str(e))
    except LoadError: raise CmdExn(f"Error loading {file}")

@miniter_command(('recover',) )
def recover_cmd(*, _env):
    load_cmd('!', params.recover_filename, _env = _env)
    os.remove(save_path(params.recover_filename))
    post_info(f"recovery succesful: '{params.recover_filename}' has been deleted", _env.context)

@miniter_command(('outline', 'out'), "$CMD width margin [paper-format]")
def export_outline_cmd(width, margin, paper = 'a4', *, _env):
    "generate printable outline with size 'width' (+ 'margin') cm"
    us_letter = (paper.lower() == 'us-letter')
    points = np.concatenate([sh.divs for sh in _env.context.shapes])
    ps_buffer = printpoints.generate(points, width, margin, us_letter)
    with open('out.ps', 'w') as out:
        out.write(ps_buffer)
    post_info("outline written to 'out.ps'", _env.context)


## Set Params
@miniter_command(('set-color', 'co'), "$CMD key OR $CMD key r g b OR $CMD hex")
def set_color_cmd(*args, _env):
    "key only: select draw color. else: change color designated by key"
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
    key = args[0].upper()
    if key not in _env.context.palette: raise CmdExn("Invalid color key")
    #
    match args[1:]:
        case []: _env.context.color_key = key
        case [hexcolor]: set_hex(hexcolor)
        case [r, g, b]: set_rgb(r, g, b)

@miniter_command(('menu',))
def show_menu_cmd(*, _env):
    "toggle menu display"
    _env.context.show_menu = not _env.context.show_menu
    _env.context.text.write_section('menu', [])

@miniter_command( ('palette', 'pal') )
def show_palette_cmd(*, _env):
    "toggle palette display"
    #
    _env.context.show_palette = not _env.context.show_palette

@miniter_command( ('div', 'nails'), "$CMD n   (n = new number of nails)")
def set_div_cmd(n, *, _env):
    "set the number of nails on the selected shapes"
    #
    if not ( 0 < n <= params.max_div) :
        raise CmdExn(f"number must be between 1 and {params.max_div}")
    unweave_into_selection(_env.context)
    for sh in _env.context.selected:
        sh.set_divs(n)

@miniter_command( ('default-divs', 'dfdiv'), "$CMD <shape_type> <default_div> ...")
def set_default_divs_cmd(*args, _env):
    "set default number of divs by shape type"
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

@miniter_command( ('weavity', 'wy'), "$CMD bound_increment loose_increment")
def set_weavity_cmd(inc0 = 1, inc1 = 1, *, _env):
    "set the 'weavity' pair. Controls spacing of strings when drawing weaves"
    #
    if inc1 == 0:
        raise CmdExn("2nd argument cannot be 0")
    _env.context.weavity = (inc0, inc1)

@miniter_command( ('weaveback', 'wb') )
def toggle_weaveback(*, _env):
    "toggle weaveback"
    _env.context.weaveback = not _env.context.weaveback

@miniter_command(('set-rotation', 'rot'), "$CMD new_angle OR $CMD p / q  (p qth of a turn)")
def set_default_rotation_cmd(*a, _env):
    "set the size of the rotation when transforming shapes"
    if len(a) != 1 and len(a) != 3: raise Exception()
    if len(a) == 3 and a[1] != '/': raise Exception()
    #
    if len(a) == 3: new_rot = 2 * pi * (a[0] / a[2])
    elif type(a[0]) == int: new_rot = 2 * pi * a[0] / 360
    elif type(a[0]) == float: new_rot = a[0]
    else: raise Exception
    _env.context.default_rotation = new_rot

# Resizing
@miniter_command( ('fullscreen', 'fu') )
def fullscreen_cmd(*, _env):
    "go fullscreen"
    #
    _env.context.screen = display.set_mode(flags = FULLSCREEN)
    resize_context(_env.context, _env.context.screen.get_width())

@miniter_command( ('resize', 'res'), "$CMD win_width win_height")
def resize_cmd(w = params.start_dimensions[0], h = params.start_dimensions[1], *, _env):
    "set window dimensions"
    #
    if w < 300 or h < 300 or w > 5000 or h > 5000:
        raise CmdExn("bad dimensions")
    _env.context.screen = display.set_mode((w, h))
    resize_context(_env.context, w)


## Grid
@miniter_command(('grid',))
def grid_cmd(*, _env):
    toggle_grid(_env.context)

def _parse_subdiv(*a):
    a = [*a]
    try:
        i, _ = next( filter( lambda i_a: (i_a[1] == ':') , enumerate(a)) )
    except StopIteration:
        i = len(a)
    return a[:i], a[i+1:]

@miniter_command(('grid-rsubdiv', 'grsub'), "$CMD non-repeating ... : repeating...")
def grid_rsubdiv_cmd(*divs, _env):
    _env.context.grid.rsubdivs = _parse_subdiv(*divs)

@miniter_command(('grid-asubdiv', 'gasub'), "$CMD non-repeating ... : repeating...")
def grid_asubdiv_cmd(*divs, _env):
    _env.context.grid.asubdivs = _parse_subdiv(*divs)


## Misc
@miniter_command(('session', 'se'), "$CMD session_name | $CMD OFF")
def connect_session(session_name, *,  _env):
    "use session <session_name> for autosaves. OFF: turn off autosaving/rewinding"
    try:
        reload_session(_env.context, session_name)
    except Autosaver.DirectoryBusyError:
        post_error("already in use.", cx)

@miniter_command(('clear', 'cl'))
def clear_cmd(*, _env):
    "clears info/error area"
    for section in {'info', 'error'}:
        _env.context.text.write_section(section, [])

@miniter_command(('select-all', 'sel*'))
def select_all_cmd(*, _env):
    "select all shapes"
    _env.context.selected = _env.context.shapes[:]

@miniter_command(('translate-colors', 'trans'), "$CMD from to  (eg $CMD qw az)")
def translate_colors_cmd(src, dest, *, _env):
    "change the colors of the weaves inside the selection"
    cx = _env.context
    src, dest = src.upper(), dest.upper()
    for i, we in enumerate(cx.weaves):
        [s1, s2] = [hg.s for hg in we.hangpoints]
        if not (s1 in cx.selected and s2 in cx.selected):
            continue
        #
        try:
            key_index = src.index(cx.weave_colors[we])
            cx.weave_colors[we] = dest[key_index]
        except: pass
    redraw_weaves(_env.context)

@miniter_command(('highlight', 'hi'), "$CMD highlighted_nail_index1 ...")
def highlight_cmd(index, *more, _env):
    "highlight the nails at the specified indices on all selected shapes"
    cx = _env.context
    cx.hints = []
    for sh in cx.selected: 
        cx.hints.extend([
            Point(sh.get_div(i)) 
            for i in [index, *more] if sh.get_div(i) is not None
            ])
    ###

@miniter_command(('source', 'so' ), "$CMD source_file")
def source_cmd(file, *, _env):
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

# Debug
@miniter_command(('_debug', '_db'))
def debug(*, _env):
    "go into python debugger"
    cx = _env.context
    breakpoint()

