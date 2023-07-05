from pygame import Color
from util import Rec

params = Rec()
params.point_radius = 2
params.snap_radius = 7

params.background = Color(0, 0, 0)
params.div_color = Color(128, 128, 128)
params.shape_color = Color(0, 128, 128)
params.hint_color = Color(128, 32, 32)
params.select_color = Color(64, 0, 192)

params.eps = 0.01
params.zoom_factor = 1.1

params.font_size = 20
params.text_color = Color(192, 192, 192)
params.error_text_color = Color(128, 32, 32)
params.term_color = Color(0, 128, 64)
