# Index
* [Intro](#intro)
* [Shapes](#shapes)
* [Weaves and Colors](#weaves-and-colors)
* [Selecting and Editing](#selecting-and-editing)
* [Undoing and Autosaves](#undoing-and-autosaves)
* [The Grid](#the-grid)
* [Saving](#saving)
* [Configuration](#configuration)
* [List of Commands](#list-of-commands)

# Intro
It is recommended that you follow along this manual by using the program.  
Place your left hand on the home row (ASDF), and use your mouse with your right hand.  
For install instructions, read the [`README`](README.md)

## Using the Menu
The bottom area of the screen displays a list of all currently available menu actions (e.g. `D: Draw Shape`), which are always activated by hitting the corresponding key on the keyboard.  
After triggering an action, the mappings will change to more contextually relevant sub-actions.  
Use `SPACE` to come back to the start of the menu. (This will also cancel currently unifinished actions)  

The bottom 4 actions (`Undo`, `Redo`, `Command` and `Change View`) are "pinned", and are available form anywhere in the menu.  

Triggering an action in the menu will often change the behavior of the mouse, and/or display a **hint at the bottom of screen**.  
For example after `D: Draw Shape`/`S: New Segment`, left-clicking on 2 points will draw a segment between them.  

## The Commandline
Some things are achieved through the command-line (i.e. by literally typing commands).  
Use `C: Command`, to enter the command-line and start typing commands. A green command prompt will appear.  
Use `Ctrl-C` to close the commandline without running the current command.

See list of available commands [here](#list-of-commands) (look first at [`help`](#help) and [`ls-cmd`](#ls-cmd)). 

Some commands have aliases. For example when this manual mentions the `help/h` command it means you can use either `help` or `h` as the command name to type.  
Sometimes in this manual, some of the aliases will be ommitted for convenience.  

Available shortcuts:
* `Ctrl-U`: erase current line
* `Ctrl-C`: cancel and close commandline
* `Ctrl-W` or `Ctrl-BackSpace`: erase last word

## Notes

* The commandline takes your keyboard layout into account, but the menu is meant to be positional and not mnemonic so it does not. As a result the labels may be wrong for your layout (they assume qwerty). You can fix this by setting the `menu_translate` parameter in the [conf](#configuration).  

* Whenever the mouse-wheel is not doing something else, you can zoom the view by scrolling.
* Nails (white points on shapes) are snappy. i.e. clicks close enough to them are treated as being **exactly** on them

* To move the view, go to `V: Change View` and right-click twice: once to grab, once to release.
* From view adjustement, you can also use the wheel to zoom regardless of what it was previously used for.
* Leaving view adjustement (with left-click) will resume whatever you were doing.

* Pink visual hints (shapes, etc) will often appear to help you understand what you're doing.

# Shapes 
To start drawing shapes go to `D: Draw Shapes`, then select the desired shape type from the menu.  
All shapes have a number of nails (white dots) on them, you can adjust it with the [`nails`](#div) or [`default-divs`](#default-divs) commands.  
You do not need to select the shape type a second time in between drawing 2 shapes of the same type.  

To draw a:
* circle: left-click on the center, then left-click on any point on the perimeter. You can use right-click to make it so the first point you clicked is on the perimeter, and the mouse controls the center.
* segment: left-click on an endpoint, then the other
* circle arc: either:
	* left-click on the center, then left-click on an endpoint of the arc, then the other (total 3 clicks). 
	* right-click (to put endpoints first), left-click on both endpoints then click the center.
	* **Note**: after placing at least 2 points (center and start or both endpoints), you can right-click to invert "clockwiseness". (which way we're going around from an endpoint to the other)
* point: left-click on the point.
* broken line: use `PolyLine` as the shape type; left-click on as many points as you want, and right-click when you're done.
* polygon: use `PolyLine` as the shape type; left-click on all the vertices, then left-click the point you started on.

Note: reminders for the above will be displayed at the bottom of the screen when you select a shape type.  

# Weaves and Colors
The colorful strings between the nails are organized in "weaves".  
Go to `F: Draw Weave` to start creating weaves.  

### Creating weaves
To create a new weave: 
* left-click a nail on any shape to define the first attach point 
* left-click another nail on another (or the same) shape to define the second attach point 
* left-click a third time on any nail on the same shape where the second attach point is to extend the weave.
* **Note:** For the first 2 attach points, if you click on a nail that is at the intersection of several shapes, you will need to choose what shape you want to use by clicking another nail on it before proceeding

A colorful string should be drawn between the first 2 attach points, and between every 2 points after them on their respective shapes until the third attach point (on the second shape) is reached, or the first shape runs out of nails.

### Choosing the weave you want
For any 3 attach points, there are up to 4 possible weaves depending on:
* The direction we're going in on the first shape. (swap with `A: invert dir`)
* For loopy shapes, whether we're going clockwise or not. (swap with `S: invert spin`)

Right-clicking will cycle through all 4 possibilities.

### "Advanced" options
Some commands affect the behavior when drawing weaves:
* `weaveback/wb`: toggles `weaveback` (on by default). If `weaveback` is enabled, a second set of colorful strings will appear to connect the previous set, as if all the lines came from a single string that wraps around the nails.
* `weavity/wy INC1 INC2`: set the "weavity" (`-1 1` by default). This allows skipping some nails. (e.g. if the weavity is `2 1`, a nail will be skipped every time when finding the "next nail" on the first shape).

## Using Colors
You can draw weaves in any of 8 different colors associated with one of the `QWERASDF` keyboard keys.  
To select what color to apply when confirming a new weave, use `E: Select Color`, then hit the key corresponding to the color you want to use.  

To customize a color use `W: Color Picker`. When you modify a color this way, the weaves that were drawn using this color will also be modified (in real time).  
In the color picker:
* use one of the `QWERASDF` keys to select the color you want to modify.
* left-click the big rainbow to choose the color to apply for this key.
* adjust the brightness of the current color with the mouse-wheel.
* repeat for every color you want to modify.
* right-click when you're done. 

# Selecting and Editing
Select and edit form the `S: Selection` submenu

### Selection basics
Left-click any nail to select all the shapes the nail belongs to (there can be several shapes if the nail is at an intersection)  
Similarly, right-click a nail to "toggle the select state" of all the shapes under it. (i.e. selected shapes become unselected and vice-versa)  
Selected shapes will be highlighted in blue.  

To select shapes within a rectangle, go to `W: Rectangle`  
* left-click twice to select the shapes inside the rectangle
* right-click to **toggle** the shapes inside the rectangle
* you can choose if to be considered inside, a shapes needs to be fully included within or if having at least a nail within is enough with `Q: Partly/Fully Within`
* use `W: Normal` to go back to single shape select

Notes: 
* you will always select shapes. (i.e. you cannot select individual nails or weaves)
* some terminal actions act on the selection
* some actions (even outside the selection submenu) will set the selection. (e.g. new shapes are selected upon creation)

`R: Remove` will delete all the currently selected shapes.  
`E: Unweave` will remove all the weaves between any two shapes that are **both** selected.  

There are two main ways to move or transform (e.g. rotate or mirror) the current selection. (detailed below)

### Editing shapes via the quick transform shortcuts (under D or F)
* Use `F: Move` to move shapes: it will **immediately** grab the point under the cursor (snappiness applies; immediately = you do not need to click). Left-click to release.
* Use `D: Quick Transform` to rotate and/or mirror currently selected shapes.
	* from there you can "stack" several transformation using the keyboard shortcuts (`S: +Rotation`, etc)
	* the center of the transformation follows the mouse snappily (e.g. rotating turns the selection **around the cursor**)
	* the angle of the rotation that is applied by `S: +Rotation` and `D: -Rotation` is configured via the `rot ANGLE` command
	* flipping is horizontal. it doesn't apply "in order", but is always the first transformation. (e.g. after `S: +Rotation`, `F: Flip`, the selection is first mirrored horizontally, then turned, regardless of the order you pressed the keys)
	* when you like the transformation (refer to the pink hints), left-click the desired center to apply
* You can put transformed copies of the current selection (instead of transforming it), by clicking `F: put copy` from either. You can click F several times in a row to repeat this effect.

### Using the intractive transformation submenu
Under `S: Interact`, you can sequentially apply several transformations to the current selection.  
Transformations are applied relative to a center (except move). Initially it is set to the center of the grid (if activated), or to the point under your cursor when you entered `S: Interact`.  
To change the center, use `A: recenter`. After left-clicking, the center is set to the point under your cursor.  

To apply transformations:
* choose the type of transformation from the menu with the keyboard. This will **immediately** grab the point under the cursor.
* move the point you grabbed to its desired position. What this means exactly depends on the type of transformation.
* either:
	* left-click to apply the transformation to the current selection. (The shapes will change)
	* right-click to create a transformed copy. The copied shapes become the selection for the next transformation.
* repeat as many times as needed
* Use `S: done` to exit the visual transformation tool.
* **Note**: You can use `Q: cancel change`, to cancel the pending change and select another type of transformation.

# Undoing and Autosaves
### Basics
You can undo/redo either with `Z: Undo`/`X: Redo`.  
Or from `R: Rewind`: scroll through the history with the mouse-wheel and click when you're done.  
The first time you make a change after an undo, it is added **at the end** of the history; so the history is not erased. Undoing right after would take you through all the savepoints you went through to get to the previous state you made the change from.  
You can still access the undo history after closing and restarting the program.  
Autosaves are not kept indefinitely, they will be progressively deleted in such a way that the history becomes sparser (more time between two savepoints) the further back in time you go.  

### Sessions
Sessions are used to bundle the history of one or several drawings together and are identified by a name. When you launch the program it will try to connect to the session `default`.  
When undoing/redoing, you will only scroll through the changes that were made while connected to the session you are currently connected to.  
Regular saves keep track of which session they are connected to. (i.e. loading will set your session to the one you were using when you saved).  

To change session use the `session SESSIONNAME` command.   
If the session does not already exist it will be created.  
The special session name `OFF` is used to indicate you want to disable undoing/autosaving.  

A session may only be used by one single running instance of the program at the any time. If you try to connect to a session that is currently being used, you will see an error message.  
Sometimes if the program is closed improperly (e.g. OS crash, etc) the program will think a session is in use when it's not. You can use the [not-in-use](#not-in-use) command to resolve such situations. Note that calling `not-in-use` when the session **is**, in fact, in use will badly mangle the undo history.  

# The Grid
You can activate/deactivate the grid either via `A: Grid`/`A: Grid on/off` or with the `grid` command.  
When the grid is on, you will see a bunch of concentric circles and angle lines to help you place points precisely.  
All the intersections of the circles and the angle lines are snappy.  
To change the center of the grid, go to `A: Grid`/`D: Grid recenter` and click the desired new center.  

You can configure the "angular subdivisions" and "radial subdivisions" via the commandline.  

For example, if the "angular subdivisions" is `5 2 : 3 2` this means:
* subdivide the central circle into 5 equal angle sectors.
* for each of these sectors subdivide it further into 2 equal subsectors
* etc
* The visible divisions will auto adjust depending on the zoom level so the view is not too cluttered. (i.e. more subdivisions will appear as you zoom)
	* You can configure the "sparseness" of the grid via `A: Grid`/`S: Grid +/- sparse`. Scroll with the mouse-wheel to adjust it.
* the subdivisions after the colon (`:`) repeat. So `5 : 2` is actually `5 2 2 2 2 ...`. If you omit it the grid will stop subdiving after a certain point regardless of zoom level.
* the "angle 0" that angular subdivisions start from can be changed by setting the "phase". By default it is horizontal to the right.
	* either via the `phase ANGLE` command.
	* or from `A: Grid`/`F: Grid set phase`, by clicking where you want the angle 0 to be.
* the angular subdivisions is set via the `grid-asubdiv/gasub SUB1 ...` command.
	* spaces around the colon are **mandatory**
	* You can omit the colon if you don't want repeating subdivisions

Similarly the "radial subdivisions" controls how the main concentric circles are divided into rings.  
Use the `grid-rsubdiv/grsub SUB1 ...` command.  

Note: see the [`sym`](#symmetrize) command for a powerful way to symmetrically extend a motif using the current grid configuration.  

# Saving
### Saving and Loading
Use the [`s/save`](#save), [`ls-saves/lsav`](#ls-saves), [`load/lo`](#load), and [`quit/q`](#quit) to save your work and quit.  
The actual save files are located at `$HOME/.qwerasdf/save`

### Exporting Outlines
You can export printable multi-page documents with marking for nails by the using `outline/out SIZE MARGIN [FORMAT]` command.
The idea is that you would stick the cut-outs over your canvas to see where the nails need to go, and tear them off later.
* `SIZE`: desired size of the drawing in cm. 
* `MARGIN`: size of the margin in cm. (i.e. the canvas is a `SIZE + MARGIN` sized square)
* `FORMAT`: paper format. (A4 if left blank; supported: `a4`, `us-letter`)

The outline will be written in the `out.ps` file. (see `exports_directory` in [conf](#configuration))
Your printer/document-viewer may or may not natively support `postscript` (`.ps`) files.  
To convert postscript to pdf files either install `ghostscript` and use the `ps2pdf` command (recommended for linux and mac) or use one of the many online postscript to pdf converters (recommended for windows).

### Exporting Images
You can export images either via the [`export-image`](#export-image) command or via the menu in `E: Export Image`.  
From the menu you can either export the current window (`R: Window`) or a centered picture of the whole drawing with a small margin (`E: Whole Drawing`).  
Use the [`image-height`](#image-height) commad to set the height (in pixels) of exported images, the width is computed from the height depending on what you're doing.  
The default format is `png` but you can set with the [`image-format`](#image-format) command.

Note: 
* The menu, current selection highlights, and other UI elements do not appear on exported images. (only shapes, nails and weaves are considered)
* Currently [hidden](#show-hide) elements, [antialasing](#antialias) settings, etc, **are** taken into account.
* Since weave strings do not have a "real" width, when exporting images with a large image height (ie higher resolution than your screen), you might want to set the drawing width higher temporarily (with [`draw-width`](#draw-width)) to avoid colors looking dull when unzoomed.  
* The `exports_directory` from the [conf](#configuration) applies to exported images.

### Using the stash
The stash is a copy-paste-like mechanism that keeps track of a short history of things that were copied.  
Use `Q: Stash` from the `S: Selection` submenu to stash the current selection, the weaves inside the selection will also be stashed.  
You can unstash (i.e. paste) previously stashed sets of shapes from the unstash submenu:
* select what to paste with `W: <=`, `E: =>`, `R: =>>|`  
* click once to grab a point on the shapes to be unstashed, 
* click a second time to release the shapes where you want them. This will put a copy

Notes:
* Some command ([import](#import)) will put things on top of the stash.
* The stash is especially convenient if you want to copy something that cannot be the current selection for some reason (Otherwise the transforms would work). For example what you want to grab comes from another file or the undo history. 
* The weaves' color depend on the **current** palette and not the one in use at copy time.

# Configuration 
### rc file
In `$HOME/.qwerasdfrc` you can write (1 per line) commands to be run every time you start the program.  
(Note: `./.qwerasfrc`, where `./` is the working directory is also read (after), but what "working directory" means will be OS dependent)  

### Setting parameters
Some parameters can be tweaked by writing configuration files.  
Conf files must be located in `$HOME/.qwerasdf` and have the `.conf` extension.  
The content has the `PARAM = VALUE` format, (1 param per line).  
Colors can be written as `r, g, b` or `hhhhhh` (where h is an hex digit).  
Some useful examples can be found in the [`example.conf`](example.conf) file.  

Parameter | Value (; allowed range) | Description
---|---|---
`background` | color | background color
`shape_color` | color | default color for shapes
`select_color` | color | color for selected shapes
`hint_color` | color | color for visual hints
`grid_color` | color | grid graduations color (brightest)
`grid_fade_factor` | float; [0.01, 0.99] | smaller = subdivisions levels get dimmer faster
`grid_sparseness_scroll_speed` | int; [1, 25] | controls mouse-wheel speed for `Grid +/- sparse`
`point_color` | color | color of nails
`point_radius` | int; [0, 5] | radius of nails (in pixels)
`point_shape_radius` | int; [1, 10] | color of 'point' shapes and hints.
`zoom_factor` | float; [1.01, 4] | controls zooming speed. 
`brightness_scroll_speed` | float; [0.005, 0.2] | controls mouse-wheel speed when in the color picker
`min_pick_saturation` | float; [0, 0.99] | controls the size of the gray band that is cut-off when rendering the color picker's rainbow
`font_size` | int; [5, 30] | size of text
`text_color` | color | default text color
`error_text_color` | color | color of error messages
`term_color` | color | color text of the commandline prompt
`snap_radius` | int; [1, 100] | min distance (in pixels) the cursor needs to be from a point to "snap" to it
`bottom_margin` | int; [0, 50] | size in pixels of the empty band below the bottom text area
`menu_translate` | keymap (e.g. `QWAZ AZQW`) | specifies key mappings (from `qwerty` to your layout) to use when displaying menu labels
`image_margin` | float; [0, 0.99] | size of the margin when exporting image (proportion of total image size) 
`exports_directory` | OS path | directory where to put exported files (images, outlines) (this does not affect saves)

# List of Commands
[help](#help), [ls-cmd](#ls-cmd), [usage](#usage), [save](#save), [remove-save](#remove-save), [ls-saves](#ls-saves), [load](#load), [exit](#exit), [new](#new), [import](#import), [recover](#recover), [outline](#outline), [image-height](#image-height), [image-format](#image-format), [export-image](#export-image), [set-color](#set-color), [menu](#menu), [palette](#palette), [div](#div), [default-divs](#default-divs), [weavity](#weavity), [weaveback](#weaveback), [set-rotation](#set-rotation), [fullscreen](#fullscreen), [resize](#resize), [grid](#grid), [grid-rsubdiv](#grid-rsubdiv), [grid-asubdiv](#grid-asubdiv), [set-phase](#set-phase), [antialias](#antialias), [draw-width](#draw-width), [show-hide](#show-hide), [stash-capacity](#stash-capacity), [session](#session), [clear](#clear), [select-all](#select-all), [translate-colors](#translate-colors), [unweave-color](#unweave-color), [raise](#raise), [symmetrize](#symmetrize), [highlight](#highlight), [source](#source), [oneshot-commands](#oneshot-commands), [not-in-use](#not-in-use), [_debug](#_debug)

### help
aliases: `help`/`h`
```
help CMD: show documentation for CMD
```

### ls-cmd
aliases: `ls-cmd`/`ls`
```
ls-cmd: list available commands
ls-cmd SEARCH: list commands matching SEARCH (by-name)
```

### usage
aliases: `usage`/`us`
```
usage CMD: show command usage
```

### save
aliases: `save`/`s`
```
save SAVENAME ! : save as SAVENAME
save SAVENAME   : same as above but forbid overwriting existing save.
save !          : save (using the previous SAVENAME)
```

### remove-save
aliases: `remove-save`/`rm`
```
remove-save SAVE1 ...: delete saves
```

### ls-saves
aliases: `ls-saves`/`lsav`
```
ls-saves            : list all existing save names
ls-saves SEARCHTERM : list all existing save names matching the search
Search Criterion: all letters appears in order. (eg 'ac' matches 'abc' but not 'ca')
If the search term is a complete name, list only it (and not other matches)
```

### load
aliases: `load`/`lo`
```
load SEARCHSAVE ! : find matches for SEARCHSAVE according to 'ls-saves' rules, and load the save if a single match is found.
load SEARCHTERM   : same as above but forbids discarding unsaved changes
```

### exit
aliases: `exit`/`quit`/`q`
```
exit   : quit program. forbids discarding unsaved changes.
exit ! : quit program.
exit SAVENAME: save as savename, then quit program.
```

### new
aliases: `new`/`blank`
```
new   : clear canvas and start new drawing. forbids discarding unsaved changes.
new ! : clear canvas and start new drawing.
new SAVENAME: save as savename, then clear canvas and start new drawing.
```

### import
aliases: `import`/`imp`
```
import SAVENAME: load SAVENAME **on top** of the stash
note: performs matching on the savename (cf load, ls-saves)
```

### recover
aliases: `recover`
```
recover: try to recover state from a previous crash
```

### outline
aliases: `outline`/`out`
```
outline WIDTH_CM MARGIN_CM: generate multi-page printable outline for drawing.
(cf. manual. (Saving section))
```

### image-height
aliases: `image-height`/`imh`
```
image-height HEIGHT: set height in pixel of exported images
```

### image-format
aliases: `image-format`/`image-extension`/`ext`
```
image-format EXTENSION: set format to use when exporting images
```

### export-image
aliases: `export-image`/`exp`
```
export-image win HEIGHT: export an HEIGHT pixels high png image of the window
export-image all HEIGHT: export an HEIGHT pixels high png image of the whole drawing
export-image ... FORMAT: same as above, but FORMAT is the image format (png, jpeg, tga)
```

### set-color
aliases: `set-color`/`co`
```
set-color KEY       : select color KEY for drawing.
set-color KEY R G B : set color KEY by RGB
set-color KEY HHHHHH: set color KEY by hexcode
```

### menu
aliases: `menu`
```
menu: show/hide menu
```

### palette
aliases: `palette`/`pal`
```
palette: show/hide palette
```

### div
aliases: `div`/`nails`/`n`
```
div N: set the number of nails on all selected shapes to N. (evenly spaced)
```

### default-divs
aliases: `default-divs`/`dfdiv`/`dfnails`
```
default-divs SHAPE_TYPE1 DEFAULT_NAILS1 ...: all shapes of type SHAPE_TYPE1 will be initially drawn with DEFAULT_NAILS1 nails.
Shape types: 'circle', 'line', 'arc', 'poly'
Can specify several (type, dfnails) pairs at once (after each other).
```

### weavity
aliases: `weavity`/`wy`
```
weavity BOUND_INCREMENT LOOSE_INCREMENT: set the weavity pair. (cf Weaves section of manual)
```

### weaveback
aliases: `weaveback`/`wb`
```
weaveback: toggle weaveback
```

### set-rotation
aliases: `set-rotation`/`rot`
```
set-rotation DEG   : set the default rotation angle to DEG degrees
set-rotation RAD pi: set the default rotation angle to RAD * pi radians. (literally type 'pi')
set-rotation P / Q : set the default rotation to P Qth of a turn. (spaces around the slash mandatory)
```

### fullscreen
aliases: `fullscreen`/`fu`
```
fullscreen: go fullscreen
```

### resize
aliases: `resize`/`res`
```
resize WIDTH HEIGHT: resize window
```

### grid
aliases: `grid`
```
grid: enable/disable grid
```

### grid-rsubdiv
aliases: `grid-rsubdiv`/`grsub`
```
grid-rsubdiv DIV1 ... : REPEAT1 ... -> set the 'radial subdivison' of the grid.
grid-rsubdiv N -> divide the central circle into N rings
grid-rsubdiv N M -> subdivide each ring further into M subrings
...
```

### grid-asubdiv
aliases: `grid-asubdiv`/`gasub`
```
grid-asubdiv DIV1 ... : REPEAT1 ...-> set the 'angular subdivison' of the grid.
grid-asubdiv N -> divide the canvas into N equal angle subsectors
grid-asubdiv N M -> divide each of the above sectors further into M subsectors
...
```

### set-phase
aliases: `set-phase`/`phase`/`ph`
```
set-phase DEG   : set the grid phase to DEG degrees
set-phase RAD pi: set the grid phase to RAD * pi radians. (literally type 'pi')
set-phase P / Q : set the grid phase to P Qth of a turn. (spaces around the slash mandatory)
```

### antialias
aliases: `antialias`/`aa`
```
antialias: toggle antialasing for drawing weave strings
```

### draw-width
aliases: `draw-width`/`width`
```
draw-width WIDTH: set width (in pixels) for drawing weave strings
```

### show-hide
aliases: `show-hide`/`shi`
```
show-hide THING1 ...: show/hide certains types of elements (shapes, weaves, nails)
```

### stash-capacity
aliases: `stash-capacity`/`stashcap`
```
stash-capacity CAPACITY: set stash capacity (ie max number of stashed items)
```

### session
aliases: `session`/`se`
```
session            : tell current session.
session SESSIONNAME: connect to session SESSIONNAME.
session OFF        : disable undoing/autosaving. (literally type 'OFF' as the SESSIONNAME)
```

### clear
aliases: `clear`/`cl`
```
clear: clear error/info messages
```

### select-all
aliases: `select-all`/`sel*`
```
select-all: select all shapes
```

### translate-colors
aliases: `translate-colors`/`trans`
```
translate-colors FROM TO: change the colors of the weaves inside the selection according to conversion rule
ex: if FROM = Q and TO = A, weaves with color Q will turn to color A
```

### unweave-color
aliases: `unweave-color`/`unco`
```
unweave-color COLORKEYS: remove all weaves of a color in colorkeys inside the selection
```

### raise
aliases: `raise`
```
raise COLORS: raise weaves inside the selection of certain colors on top
(last on top)
```

### symmetrize
aliases: `symmetrize`/`sym`
```
symmetrize PATTERN COLORSFROM COLORSTO: complete a circle around the grid, making rotated copies of the selection
example of patterns: r, r1 (same as r), r2, s, s3, 2 (same as r2), (nothing) (same as r1)...
rn: create copies by rotating by n * the grid sector angle
sn: same as rn, but make an horizontally mirrored copy before rotating
if COLORSFROM and COLORSTO are specified, change colors as if by translate-colors after every transform
```

### highlight
aliases: `highlight`/`hi`
```
highlight INDEX1 ...: highlight the nails at the specified indices on all selected shapes
```

### source
aliases: `source`/`so`
```
source CMDSFILE: read CMDSFILE, and execute its lines as commands
```

### oneshot-commands
aliases: `oneshot-commands`/`one`
```
oneshot-commands: toggle oneshot commands. (default: enabled)
when enabled: the commandline closes after every command
```

### not-in-use
aliases: `not-in-use`
```
not-in-use SESSION: Allow later connection to SESSION in spite of the "not in use" error.
not-in-use: same as: not-in-use default
Note that if SESSION is actually in use, this will badly mangle your undo history
```

### \_debug
aliases: `_debug`/`_db`
```
_debug: go into python debugger
```

