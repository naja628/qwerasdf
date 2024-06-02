from os import environ, path, makedirs
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# Try to load save the icon with the other files
try:
    # apparently `os` doesn't have a `copy` or something function
    def fcopy(src, dest):
        try:
            i, o = open(src, 'rb'), open(dest, 'wb')
            o.write(i.read())
        finally:
            i.close()
            o.close()

    _install_icon = path.expanduser('~/.qwerasdf/data/icon.png')
    if not path.isfile(_install_icon):
        makedirs( path.dirname(_install_icon), exist_ok=True )
        icon = path.join(path.dirname(__file__), 'data/icon.png')
        fcopy(icon, _install_icon)
except: pass # don't die if we have icon problems

from .run import main
