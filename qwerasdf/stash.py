from collections import deque

from .util import Rec
from .context import copy_weaves_inside
from .shape import bounding_rect
from .params import params

class Stash:
    def __init__(self):
        self.items = deque()
        self.cap = params.initial_stash_cap
    #
    def set_cap(self, cap):
        if cap < 0: cap = 0
        self.cap = cap
        self.items = self.items[:cap]
    #
    def most_recent(self):
        return self.items[0]
    #
    def pop(self): # pop oldest
        return self.items.pop()
    #
    def _push(self, item):
        self.items.appendleft(item)
        if len(self.items) > self.cap:
            self.items.pop()
            self.index += 1
    #
    def __getitem__(self, i):
        return self.items[i]
    #
    def __len__(self):
        return len(self.items)
    #
    def push_shapes(self, shapes, context):
        if not shapes: return
        #
        vmin, vmax = bounding_rect(*shapes)
        center = (vmin + vmax) / 2
        stash_frame = Rec()
        stash_frame.shapes = [sh.moved(-center) for sh in shapes]
        stash_frame.weaves, stash_frame.weave_colors = copy_weaves_inside(
                stash_frame.shapes, shapes, context.weaves, 
                context, create = False, return_colors = True)
        #
        self._push(stash_frame)
    #
