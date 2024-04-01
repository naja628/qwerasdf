from pygame import K_SPACE

from .text import TextArea
from .params import ptol, ltop

class Menu:
    class Shortcut:
        def __init__(self, path): self.path = path
        def get(self): return self.path
    ###
    def __init__(self, nested = {}, pinned = {}, layout = [], space_action = None):
        self.layout = layout
        #
        self._path = ""
        self.root = nested
        self.pos = self.root # pos is always a dict
        #
        self.pinned = pinned
        self.temp_show = {}
        self.temp_show_mask = ''
        #
        self.space_action = space_action
    #
    def _is_leaf(self, thing):
        return type(thing) is str
    #
    def go(self, key, navigate = True):
        if key == K_SPACE:
            return self.space_action
        if key in self.pinned:
            return self.pinned[key]
        #
        if key in self.pos:
            down = self.pos[key]
            if self._is_leaf(down):
                return down
            else:
                if navigate:
                    if type(down[1]) is dict: self.pos = down[1]; self._path += key
                    elif type(down[1]) is Menu.Shortcut: self.go_path(down[1].get())
                    else: assert False
                return down[0]
        else:
            return None
    #
    def __getitem__(self, key):
        return self.go(key, navigate = False)
    #
#     def go_path(self, path):
#         self.pos = self.root
#         self._path = ""
#         for (i, key) in enumerate(path):
#             if self.go(key) == None:
#                 self._path = path[:i]
#                 break
    def go_path(self, path):
        if path == None: path = self._path
        #
        self.pos = self.root
        self._path = ""
        prev, current = None, None
        for (i, key) in enumerate(path):
            current = self.go(key)
            if current == None:
                self._path = path[:i]
                return prev
            prev = current
        return current
    #
    def path(self):
        return self._path
    #
    def up(self, n = 1): # 0 go to root
        self.go_path(self._path[:-n])
    #
    def temporary_display(self, mask, items):
        self.temp_show_mask = mask
        self.temp_show = items
    #
    def restore_display(self):
        self.temporary_display('', {})
    #
    def render(self, textbox):
        menu_layout = self.layout
        #
        label_size = 15
        #
        lines = []
        for (i, row) in enumerate(menu_layout):
            line = "|"
            for key in row:
                if key in self.temp_show_mask:
                    if key in self.temp_show: label = self.temp_show[key]
                    else: label = None
                else:
                    label = self[key]
                #
                if label:
                    line += f" {ptol(key)}: "
                    line += label[:label_size].ljust(label_size)
                else:
                    line += ' ' * (len(" X: ") + label_size)
                line += ' |'
            lines.append(line)
        if self.space_action and menu_layout:
            line_sz = (len(" | X: ") + label_size) * len(menu_layout[0]) + 1
            lines.append(f'| SPACE: {self.space_action}'.ljust(line_sz - 1) + '|')
        textbox.write_section('menu', lines)
        return textbox.render()
    ###

