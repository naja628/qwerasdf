from os import environ, path
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# apparently `os` doesn't have a `copy` or something function
def fcopy(src, dest):
    try:
        i, o = open(src, 'rb'), open(dest, 'wb')
        o.write(i.read())
    finally:
        i.close()
        o.close()

_install_icon = path.expanduser('~/.qwerasdf/icon.png')
if not path.isfile(_install_icon):
    icon = path.join(path.dirname(__file__), '../data/icon.png')
    fcopy(icon, _install_icon)

from .run import main
