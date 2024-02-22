import numpy as np
from params import params
from util import clamp

def farr(seq):
    return np.array([float(x_i) for x_i in seq])

class View:
    def __init__(self, corner = (0,0), ppu = 500):
        self.corner = farr(corner)
        self.ppu = int(ppu)
    #
    def __str__(self):
        return f"View: \n\tcorner = {self.corner}\n\tppu = {self.ppu}\n"
    #
    def ptor(self, pp):
        "pixel to real"
        (px, py) = pp
        rx = self.corner[0] + px / self.ppu
        ry = self.corner[1] - py / self.ppu
        return farr((rx, ry))
    #
    def rtop(self, rp):
        "real to pixel"
        (rx, ry) = rp
        px = int((rx - self.corner[0]) * self.ppu)
        py = -int( (ry - self.corner[1]) * self.ppu )
        return (px, py)
    #
    def ptord(self, pd):
        return pd / self.ppu
    #
    def rtopd(self, rd):
        return int(rd * self.ppu)
    #
    def rzoom(self, rcenter, factor):
        self.ppu *= factor
#         if self.ppu > params.max_ppu:
#             self.ppu = params.max_ppu
#             return
#         if self.ppu < params.min_ppu:
#             self.ppu = params.min_ppu
#             return
        if not (params.min_ppu <= self.ppu <= params.max_ppu):
            self.ppu = clamp(self.ppu, params.min_ppu, params.max_ppu)
            return
        d = self.corner - rcenter
        self.corner = rcenter + (1 / factor) * d
    #
    def zoom(self, pcenter, factor):
        self.rzoom(self.ptor(pcenter), factor)
    #
    def rmove(self, rmotion):
        self.corner += rmotion
    #
    def move(self, pmotion):
        self.rmove( self.ptor(pmotion) )
    ###

