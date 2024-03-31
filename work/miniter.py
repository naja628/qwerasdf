from pygame import display, FULLSCREEN
from numpy import pi
import os

from params import params, ltop, ptol
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

@miniter_command(('help', 'h'), "$CMD CMD")
def help_cmd(cmd_name, *, _env):
    "$CMD CMD: show documentation for CMD"
    #
    post_info(f"{miniter_command_map[cmd_name].__doc__.replace('$CMD', cmd_name)}", _env.context)

@miniter_command(('ls-cmd', 'ls'))
def list_cmd(*, _env):
    "$CMD: list available commands"
    #
    post_info( ', '.join([ aliases[0] for aliases in miniter_aliases_map.values() ]), _env.context )

@miniter_command(('usage', 'us'), "$CMD CMDNAME")
def usage_cmd(cmd_name, *, _env):
    "$CMD CMD: show command usage"
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

@miniter_command(('ls-saves', 'lsav'), "$CMD || $CMD SEARCH_TERM")
def ls_saves_cmd(search = None, *, _env):
    '''$CMD            : list all existing saves
       $CMD SEARCHTERM : list all existing matching the search
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
    if bang != '!' and bang is not None: raise Exception()
    #
    same, _ = _cmp_buff(_env.context)
    if bang != '!' and not same:
        raise CmdExn(f"Would discard changes. Use '{_env.cmd} {search_file} !' to ignore")
    #
    try:
        matches = [*_fuzzy_matches(search_file, _saves_list())]
        if len(matches) == 0: raise CmdExn(f"no match for '{load}' found")
        elif len(matches) > 1: raise CmdExn(f"found several matches: {', '.join(matches)}")
        #
        load_file = save_path( matches[0] )
        loaded_data, extra = load(load_file)
        load_to_context(_env.context, loaded_data, extra)
        #
        _env.context.last_save_buffer = save_buffer(_env.context, extra = {'session'})
        reset_menu(_env.context)
    except ParseError as e: raise CmdExn(str(e))
    except LoadError: raise CmdExn(f"Error loading {load}")

@miniter_command( ('exit', 'quit', 'q'), "$CMD || $CMD ! || $CMD SAVE")
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
#     cx.menu.go_path('')
    redraw_weaves(cx)

@miniter_command(('import', 'imp'), "$CMD SAVENAME")
def import_cmd(file, *, _env):
    "$CMD SAVENAME: load SAVENAME **on top** of existing drawing"
    try:
        import_to_context(_env.context, save_path(file))
    except ParseError as e: raise CmdExn(str(e))
    except LoadError: raise CmdExn(f"Error loading {file}")

@miniter_command(('recover',) )
def recover_cmd(*, _env):
    "$CMD: try to recover state from a previous crash"
    load_cmd('!', params.recover_filename, _env = _env)
    os.remove(save_path(params.recover_filename))
    post_info(f"recovery succesful: '{params.recover_filename}' has been deleted", _env.context)

@miniter_command(('outline', 'out'), "$CMD WIDTH_CM MARGIN_CM [PAPER_FORMAT]")
def export_outline_cmd(width, margin, paper = 'a4', *, _env):
    '''$CMD WIDTH_CM MARGIN_CM: generate multi-page printable outline for drawing.
       (cf. manual. (Saving section))'''
    us_letter = (paper.lower() == 'us-letter')
    points = np.concatenate([sh.divs for sh in _env.context.shapes])
    ps_buffer = printpoints.generate(points, width, margin, us_letter)
    with open('out.ps', 'w') as out:
        out.write(ps_buffer)
    post_info("outline written to 'out.ps'", _env.context)


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

@miniter_command( ('div', 'nails'), "$CMD N   (N = new number of nails)")
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
    if inc1 == 0:
        raise CmdExn("2nd argument cannot be 0")
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
    "$CMD DIV1 ... : REPEAT1 ...: set the 'radial subdivison' of the grid. (cf manual)"
    _env.context.grid.rsubdivs = _parse_subdiv(*divs)

@miniter_command(('grid-asubdiv', 'gasub'), "$CMD DIV1 ... : REPEAT1 ...")
def grid_asubdiv_cmd(*divs, _env):
    "$CMD DIV1 ... : REPEAT1 ...: set the 'angular subdivison' of the grid. (cf manual)"
    _env.context.grid.asubdivs = _parse_subdiv(*divs)

@miniter_command(('set-phase', 'phase', 'ph'), "$CMD new_phase")
def set_phase_cmd(*a, _env):
    '''$CMD DEG   : set the grid phase to DEG degrees
       $CMD RAD pi: set the grid phase to RAD * pi radians. (literally type 'pi')
       $CMD P / Q : set the grid phase to P Qth of a turn. (spaces around the slash mandatory)'''
    ph = _read_angle(*a)
    _env.context.grid.phase = ph

## Misc
@miniter_command(('session', 'se'), "$CMD SESSIONNAME | $CMD OFF")
def connect_session(session_name, *,  _env):
    '''$CMD SESSIONNAME: connect to session SESSIONNAME.
       $CMD OFF: disable undoing/autosaving. (literally type 'OFF' as the SESSIONNAME)'''
    try:
        reload_session(_env.context, session_name)
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

@miniter_command(('translate-colors', 'trans'), "$CMD FROM TO  (example: $CMD qw az)")
def translate_colors_cmd(src, dest, *, _env):
    '''$CMD FROM TO: change the colors of the weaves inside the selection according to conversion rule
       ex: if FROM = Q and TO = A, weaves with color Q will turn to color A'''
    cx = _env.context
    src, dest = (''.join(ltop(k) for k in ks) for ks in (src.upper(), dest.upper()))
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
