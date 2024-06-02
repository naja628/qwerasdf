import numpy as np
from math import ceil

from .params import params
eps = params.eps

_box_margin = 0.7 # in cm
# printers apparently can't print right to edge of the page, and 7mm is safe-ish for 
# most commercial models

_preface = '''
/cm {2.54 div 72 mul} def
/mm {10 div cm} def

/margin {7 mm} def
/border {0.6 mm} def

/halfwidth {0.2 cm} def
/p {
	cm exch cm exch
	2 copy
	moveto
	halfwidth neg 0 rmoveto
	halfwidth 2 mul 0 rlineto
	stroke
	moveto
	0 halfwidth neg rmoveto
	0 halfwidth 2 mul rlineto
	stroke
} def

% label width height strokebox
/strokebox {
	cm exch cm exch
    /h exch def
    /w exch def
    %
	margin dup translate
    %
    0 h 2 mm add moveto
    /Courier findfont
    20 scalefont
    setfont
    show
    %
	0 0 moveto
    w 0 rlineto
    0 h rlineto
    w neg 0 rlineto
    closepath
	gsave
		border setlinewidth
		.5 setgray
		stroke
	grestore
	gsave
		1 setgray
		fill
	grestore
	clip
	newpath
} def
'''


def generate(points, width, margin, us_letter = False):
    pagewidth, pageheight = 596, 842 # A4
    if us_letter: 
        pagewidth, pageheight = 612, 792 
    preface = f'<</PageSize [{pagewidth} {pageheight}]>> setpagedevice\n' + _preface
    # fit the points
    dims = np.amax(points, 0) - np.amin(points, 0) 
    if dims[0] < eps and dims[1] < eps:
        return ''
    if dims[0] > dims[1]: scale = width / dims[0] 
    else: scale = width / dims[1]
    #
    points -= np.amin(points, 0)
    points *= scale
    points += np.array([margin, margin])
    #
    avail_width = pagewidth * (2.54 / 72) - 2 * _box_margin 
    dims *= scale
    dims += 2 * margin
    [pages_wide, pages_high] = [ int(ceil( l / avail_width )) for l in dims]
    npages = pages_wide * pages_high
    point_sections = [''] * npages
    def i(x, y):
        y = pages_high - 1 - y # reverse
        return y * pages_wide + x
    for p in points:
        x_page, x = int(p[0] // avail_width), p[0] % avail_width
        y_page, y = int(p[1] // avail_width), p[1] % avail_width
        point_sections[i(x_page, y_page)] += f'{x:.3f} {y:.3f} p\n'
    #
    pages = [''] * npages
    for x in range(pages_wide):
        for y in range(pages_high):
            w = avail_width if x != pages_wide - 1 else dims[0] % avail_width
            h = avail_width if y != pages_high - 1 else dims[1] % avail_width
            pages[i(x,y)] = ''.join([
                "gsave\n",
                f"({x + 1}x{pages_high - y}/{pages_wide}x{pages_high}) {w} {h} strokebox\n",
                point_sections[i(x,y)],
                "showpage\n",
                "grestore\n",
                ])
    ###
    return preface + ''.join(pages)

