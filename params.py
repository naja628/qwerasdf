import os.path
from pygame import Color

#############################
start_dimensions = (800, 800)

save_dir = './save'
recover_filename = 'RECOVER.qw'
dotrc = os.path.expanduser('~/.qwerasdfrc')

background = Color(0, 0, 0)
div_color = Color(128, 128, 128)
shape_color = Color(0, 128, 128)
hint_color = Color(128, 32, 32)
select_color = Color(64, 0, 192)

start_palette = {
 'Q': Color(192, 32, 96),
 'W': Color(64, 192, 16),
 'E': Color(64, 0, 192),
 'R': Color(192, 128, 0),
 #
 'A': Color(160, 200, 128),
 'S': Color(192, 192, 128),
 'D': Color(192, 96, 32),
 'F': Color(192, 32, 160),
 }

font_size = 15
text_color = Color(192, 192, 192)
error_text_color = Color(128, 32, 32)
term_color = Color(0, 128, 64)

start_ndivs = 60
point_radius = 2 
snap_radius = 7

eps = 0.01 # distance under which two points are considered "the same"
zoom_factor = 1.1

