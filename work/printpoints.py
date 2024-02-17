import numpy as np
from math import ceil

from params import eps

preface = '''%!
/cm {2.54 div 72 mul} def
/mm {10 div cm} def

% A4 
/pagewidth 21 cm def
/pageheight 29.7 cm def

/margin {7 mm} def
/border {0.6 mm} def
/side {pagewidth margin 2 mul sub} def

<</PageSize [pagewidth pageheight]>> setpagedevice

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

/setbox {
	margin dup translate
	0 0 moveto
	side 0 rlineto
	0 side rlineto
	side neg 0 rlineto
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

def generate(points, width, margin):
    # fit the points
    dims = np.amax(points, 0) - np.amin(points, 0) 
    if dims[0] < eps and dims[1] < eps:
        return ''
    if dims[0] > dims[1]: scale = width / dims[0] 
    else: scale = width / dims[1] # TODO problem with centering?
    #
    points -= np.amin(points, 0)
    points *= scale
    points += np.array([margin, margin])
    #
    square_side = 21 - 2 * (0.7) # A4 with 7mm margins, TODO don't hardcode
    #
    dims *= scale
    [pages_wide, pages_high] = [ int(ceil( (l + 2*margin) / square_side )) for l in dims]
    npages = pages_wide * pages_high
    point_sections = [''] * npages
    for p in points:
        ix_page, x = int(p[0] // square_side), p[0] % square_side
        iy_page, y = int(p[1] // square_side), p[1] % square_side
        iy_page = pages_high - 1 - iy_page
        point_sections[iy_page*pages_wide + ix_page] += f'{x} {y} p\n'
    #
    pages = [f'gsave\nsetbox\n{points}showpage\ngrestore\n' for points in point_sections]
    return preface + ''.join(pages)

