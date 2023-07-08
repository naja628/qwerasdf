from pygame import display, FULLSCREEN

import params
from context import g
from util import Rec, param_decorator, eprint
from text import *
from save import *

# set by `miniter_command` decorator
miniter_aliases_map = {} # cmd funs to aliases (ie command names)
miniter_usage_map = {} # cmd funs to usage messages
miniter_command_map = {} # aliases to cmd funs 

def miniter_exec(cmd, context = g):
    return term_exec(cmd, miniter_command_map, miniter_usage_map, context = g)
#
def term_exec(cmd, cmd_map, usage_map, context = g):
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
            post_error("Command not found", context = context)
            return 1
        cmd_map[cmd](*args, **kwargs)
        return 0
    # for debug (just show the python exception)
    # except BaseException as e: post_error(str(e), context = context)
    except CmdExn as e: 
        post_error(str(e), context = context); return e.exit_code
    except BaseException as e:
        try:
            eprint('debug info: term caught', type(e), e)
            usage_msg = usage_map[cmd_map[cmd]].replace('$CMD', cmd)
            post_error(usage_msg, context = context)
        except BaseException as e:
            eprint('debug info: term REcaught', type(e), e)
            post_error(str(e), context = context)
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

def _slash_aliases(cmd_name):
    return '/'.join(miniter_aliases_map[miniter_command_map[cmd_name]])

@miniter_command(('help', 'h'), "$CMD cmd_name")
def help_cmd(cmd_name, *, _env):
    "get description of command"
    #
    post_info(f"{_slash_aliases(cmd_name)}: {miniter_command_map[cmd_name].__doc__}")

@miniter_command(('ls_cmd', 'ls'))
def list_cmd(*, _env):
    "list available commands"
    #
    post_info( ', '.join([ aliases[0] for aliases in miniter_aliases_map.values() ]) )

@miniter_command(('usage', 'us'), "$CMD cmd_name")
def usage_cmd(cmd_name, *, _env):
    "show command usage"
    #
    cmd_names = '/'.join(miniter_aliases_map[miniter_command_map[cmd_name]])
    usage_str = miniter_usage_map[miniter_command_map[cmd_name]]
    post_info(usage_str.replace('$CMD', cmd_names), context = _env.context)

@miniter_command(('set_color', 'co'), "$CMD key OR $CMD key r g b OR $CMD hex")
def set_color_cmd(*args, _env):
    "key only: select draw color. else: change color designated by key"
    #
    palette = _env.context.palette
    #
    def set_rgb(r, g, b):
        palette[key] = Color(r, g, b)
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
    if key not in palette: raise CmdExn("Invalid color key")
    #
    match args[1:]:
        case []: _env.context.color_key = key
        case [hexcolor]: set_hex(hexcolor)
        case [r, g, b]: set_rgb(r, g, b)

@miniter_command( ('palette', 'pal') )
def show_palette_cmd(*, _env):
    "show palette toggle"
    #
    _env.context.show_palette = not _env.context.show_palette

@miniter_command( ('div', 'nails'), "$CMD n   (n = new number of nails)")
def set_div_cmd(n, *, _env):
    "set the number of nails on the selected shapes"
    #
    if not ( 0 < n <= params.max_div) :
        raise CmdExn(f"number must be between 1 and {params.max_div}")
    for sh in _env.context.selected:
        sh.set_divs(n)

@miniter_command( ('weavity', 'wy'), "$CMD bound_increment free_increment")
def set_weavity_cmd(inc0 = 1, inc1 = 1, *, _env):
    "set the 'weavity' pair. Controls spacing of string when drawing weaves"
    #
    if inc1 == 0:
        raise CmdExn("2nd argument cannot be 0")
    _env.context.weave_incrs = (inc0, inc1)

@miniter_command( ('fullscreen', 'fu') )
def fullscreen_cmd(*, _env):
    "go fullscreen"
    #
    g.screen = display.set_mode(flags = FULLSCREEN)
    _env.context.text_area.set_surface(display.get_window_size()[0])

@miniter_command( ('resize', 'res'), "$CMD win_width win_height")
def resize_cmd(w = params.start_dimensions[0], h = params.start_dimensions[1], *, _env):
    "set window dimensions"
    #
    if w < 300 or h < 300 or w > 9000 or h > 9000:
        raise CmdExn("bad dimensions")
    _env.context.screen = display.set_mode((w, h))
    _env.context.text_area.set_surface(display.get_window_size()[0])

@miniter_command( ('exit', 'quit', 'q'), "$CMD save_to OR $CMD !}")
def exit_cmd(save_or_bang, *, _env):
    "save and exit. use ! instead of save-name to skip saving"
    #
    if save_or_bang != '!':
        save(save_path(save_or_bang), overwrite_ok = True)
    g.QUIT = True

_last_save_filename = None
@miniter_command(('save', 's'), "$CMD file OR $CMD ! OR $CMD ! file")
def save_cmd(*a, _env):
    "save. with ! : overwrite previous save"
    #
    global _last_save_filename
    if not (1 <= len(a) <= 2): raise Exception()
    try:
        if a[0] == '!':
            file = _last_save_filename if len(a) == 1 else a[1]
        else:
            file = a[0]
        if file == None: raise CmdExn("No previous savename")
        overwrite_ok = (a[0] == '!')
        save(save_path(file), overwrite_ok, _env.context)
        _last_save_filename = file
    except FileExistsError:
        raise Exn(f"'{file}' exists. to allow overwrites, use: {_env.cmd} ! {file}")

@miniter_command(('load', 'lo'), "$CMD save_to load_from OR $CMD ! load_from")
def load_cmd(save, load, *, _env):
    "save then load. use ! instead of save-name to skip saving"
    #
    if save != '!':
        try:
            save(save_path(save), overwrite_ok = False, context = _env.context)
        except FileExistsError:
            raise CmdExn(f"{save} exists. maybe you meant 'lo ! {save}'")
    #
    try:
        load_to_context(save_path(load), _env.context)
        if (save_path(load) == save_path(params.recover_filename)):
            os.remove(save_path(load))
            post_info(f"recovery succesful: '{params.recover_filename}' has been deleted")
    except ParseError as e: raise CmdExn(str(e))
    except LoadError: raise CmdExn(f"Error loading {load}")

@miniter_command(('clear', ))
def clear_cmd(*, _env):
    "clears info/error area"
    #
    for line in ERRLINE, INFOLINE:
        _env.context.text_area.set_line(line, '')
    #

