import os.path
from pygame import Color

#############################
start_dimensions = (800, 800)

save_dir = './save'
recover_filename = 'RECOVER.qw'
autosave_dir = './autosave'
#dotrc = os.path.expanduser('~/.qwerasdfrc')
dotrc = '.qwerasdfrc'

background = Color(0, 0, 0)
# shape_color = Color(0, 128, 128)
shape_color = Color(32, 64, 64)
hint_color = Color(128, 32, 96)
select_color = Color(64, 0, 192)

point_radius = 1
div_color = Color(128, 128, 128)

start_palette = {
 'Q': Color(192, 32, 96),
 'W': Color(11, 153, 20),
 'E': Color(64, 0, 192),
 'R': Color(192, 128, 0),
 #
 'A': Color(160, 200, 128),
 'S': Color(0, 200, 100),
 'D': Color(192, 96, 32),
 'F': Color(100, 0, 200),
 }

font_size = 15
text_color = Color(192, 192, 192)
error_text_color = Color(128, 32, 32)
term_color = Color(0, 160, 128)

term_xx_close = True # typing 'xx' or 'XX' at the end of the prompt will close the terminal

start_ndivs = 60 # TODO used anywhere?
snap_radius = 9

zoom_factor = 1.1

brightness_scroll_speed = 0.025
min_pick_saturation = 0.2

# touch at own risk
eps = 0.0000001 # distance under which two points are considered "the same"
max_div = 1000
max_ppu = 1e6
min_ppu = 1e-5

autosave_pulse = 2
autosave_rotorctl = [ (30, 3) ] * 5 + [ 30 ]
