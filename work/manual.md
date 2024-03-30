# Basics
Place your left hand on the home row (ASDF), and use your mouse with your right hand.

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
To quit the command-line use `Ctrl-C` or use `Enter` when the prompt is empty (no text was typed since the last command).  

See list of available commands (look first at `help` (TODO link) and `ls-cmd` (TODO link)). [TODO link]  

Some commands have aliases. For example if I talk about the `help/h` command it means you can use either `help` or `h` as the command name to type.  
Sometimes in this manual, I will omit some of the aliases for convenience.  

Available shortcuts:
* `Ctrl-U`: erase current line
* `Ctrl-C`: cancel and close commandline
* `Ctrl-W` or `Ctrl-BackSpace`: erase last word

## Notes

* Whenever the mouse-wheel is not doing something else, you can zoom the view by scrolling.
* Nails (Points on shapes) are snappy. i.e. clicks close enough to them are treated as being **exactly** on them

* To move the view, go to `V: Change View` and right-click twice: once to grab, once to release.
* From view adjustement, you can also use the wheel to zoom regardless of what it was previously used for.
* Leaving view adjustement (with left-click) will resume whatever you were doing.

* Pink visual hints (shapes, etc) will often appear to help you understand what you're doing.

# Drawing Shapes 
To start drawing shapes go to `D: Draw Shapes`, then select the desired shape type from the menu.  
All shapes have a number of nails (white dots) on them, you can adjust it with the `nails` or `default-divs` commands. (TODO link).  
You do not need to select the shape a second type in between drawing 2 shapes of the same type.  

To draw a:
* circle: left-click on the center, then left-click on any point on the perimeter. You can use right-click to make it so the first point you clicked is on the perimeter, and the second controls the center.
* segment: left-click on an endpoint, then the other
* circle arc: left-click on the center, then left-click on an endpoint of the arc, then the other. Use right-click to toggle whether you're going clockwise.
* point: left-click on the point.
* broken line: use `PolyLine` as the shape type; left-click on as many points as you want, and right-click when you're done.
* polygon: use `PolyLine` as the shape type; left-click on all the vertices, then left-click the point you started on.

Note: reminders for the above will be displayed at the bottom of the screen when you select a shape type.

# Drawing Weaves (and working with colors)
The colorful strings between the nails are organized in "weaves".
Go to `F: Draw Weave` to start creating weaves.

### Creating Weaves
To create a new weave: 
* left-click a nail on any shape to define the first attach point 
* left-click another nail on another (or the same) shape to define the second attach point 
* left-click a third time on any nail on the same shape where the second attach point is to extend the weave.
* **Note:** For the first 2 attach points, if you click on a nail that is at the intersection of several shapes, you will need to choose what shape you want to use by clicking another nail on it before proceeding
(TODO either mention the selection thing or remove the code for it)

A colorful string should be drawn between the first 2 attach points, and between every 2 points after them on their respective shapes until the third attach point (on the second shape) is reached, or the first shape runs out of nails.

### Choosing the weave you want
For any 3 attach points, there are up to 4 possible weaves depending on:
* The direction we're going in on the first shape. (swap with `A: invert dir`)
* For loopy shapes, whether we're going clockwise or not. (swap with `S: invert spin`)

Right-clicking will cycle through all 4 possibilities.

### "Advanced" Options
Some commands affect the behavior when drawing weaves:
* `weaveback/wb`: toggles `weaveback` (on by default). If `weaveback` is enabled, a second set of colorful strings will appear to connect the previous set, as if all the lines came from a single string that wraps around the nails.
* `weavity/wy INC1 INC2`: set the "weavity" (1 -1 by default). This allows skipping some nails. (e.g. if the weavity is 2 1, a nail will be skipped every time when finding the "next nail" on the first shape).

## Using Colors
You can draw weaves in any of 8 different colors associated with one of the `QWERASDF` keyboard keys.  
To select what color to apply when confirming a new weave, use `E: Select Color`, then hit the key corresponding to the color you want to use.  

To customize a color use `W: Color Picker`. When you modify a color this way, the weaves that were drawn using this color will also be modified (in real time).  
In the color picker:
* use one of the `QWERASDF` keys to select the color you want to modify.
* left-click the big rainbow to choose the color to apply for this key.
* repeat for every color you want to modify.
* right-click when you're done. 

# Selecting and Editing
Select and edit form the `S: Selection` submenu

### Selection basics
Left-click any nail to select all the shapes the nail belongs to (there can be several shapes if the nail is at an intersection)
Similarly, right-click a nail to "toggle the select state" of all the shapes under it. (i.e. selected shapes become unselected and vice-versa)
Selected shapes will be highlighted in blue.
Notes: 
* you will always select shapes. (i.e. you cannot select individual nails or weaves)
* some terminal actions act on the selection
* some actions (even outside the selection submenu) will set the selection. (e.g. new shapes are selected upon creation)

`R: Remove` will delete all the currently selected shapes.
`E: Unweave` will remove all the weaves between two shapes that are **both** selected.

There are two main ways to move or transform (e.g. rotate or mirror) the current selection. (detailed below)

### Editing shapes via the quick edit shortcuts (under ASDF)
* Use `D: Move` to move shapes: it will **immediately** grab the point under the cursor (snappiness applies; immediately = you do not need to click). Left-click to release.
* Use `A: Transform` to rotate and/or mirror currently selected shapes.
	* from there you can "stack" several transformation using the keyboard shortcuts (`S: +Rotation`, etc)
	* the center of the transformation follows the mouse snappily (e.g. rotating turns the selection **around the cursor**)
	* the angle of the rotation that is applied by `S: +Rotation` and `D: -Rotation` is configured via the `rot ANGLE` command
	* flipping is horizontal. it doesn't apply "in order", but is always the first transformation. (e.g. after `S: +Rotation`, `F: Flip`, the selection is first mirrored horizontally, then turned, regardless of the order you pressed the keys)
	* when you like the transformation (refer to the pink hints), left-click the desired center to apply
* The `Copy-transform` and `Copy-move` variants work as above, but a copy of the selection with the transformation applied will be created.

### Using the visual transformation submenu
Under `W: Visual`, you will be sequentially apply several transformations to the shape.   
Transformation are applied relative to a center (except move). Initially it is set to the center of the grid (if activated, TODO), or to the point under your cursor when you under `W: visual`.  
To change the center, use `R: recenter`. The center is set **immediately** to the point under your cursor.

To apply transformations:
* choose the type of transformation from the menu with the keyboard. This will **immediately** grab the point under the cursor.
* move your the point you grabbed to its desired position. What this means exactly depends on the type of transformation.
* either:
	* left-click to apply the transformation to the current selections. (The shapes will change)
	* right-click to create a transformed copy. The created shapes become the selection for the next transformation.
* repeat as many times as needed
* Use `W: done` to exit the visual transformation tool.
* **Note**: You can use `Q: cancel change`, to cancel the pending change and select another type of transformation.

# Undoing and the autosave system (sessions)
### Basics
You can undo/redo either with `Z: Undo`/`X: Redo`.  
Or from `R: Rewind`: scroll through the history with the mouse-wheel and click when you're done.  
The first time you make a change after an undo, it is added **at the end** of the history; so the history is not erased. Undoing right after would take you through all the savepoints you went through to get to the previous state you made the change from.  
You can still access the undo history after closing and restarting the program.  

### Sessions
Sessions are used to bundle the history of one or several drawing together and are identified by a name. When you launch the program it will try to connect to the session `default`.  
When undoing/redoing, you will only scroll through the changes that were made while connected to the session you are currently connected to.  
Regular saves keep track of which session they are connected to. (i.e. loading will set your session to the one you were using when you saved).  

To change session use the `session SESSIONNAME` command.   
If the session does not already exist it will be created.  
The special session name `OFF` is used to indicate you want to disable undoing/autosaving.  

A session may only be used by one single running instance of the program at the same time. If you try to connect to a session that is currently being used, you will see an error message.

Note: the raw data of the the autosave history is located at `$YOUR_HOME/.qwerasdf/autosave` (TODO currently not true)

# The Grid
You can activate (toggle) the grid either via `A: Grid`/`A: Grid on/off` or with the `grid` command.  
When the grid is on, you will see a bunch of concentric circles and radial subdivisions to help you place points precisely.  
All the intersections of the circles and the radial lines are snappy.  
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
* the angular subdivisions is set via the `grid-asubdiv/gasub SUB1 ... ` command.
	* spaces around the colon are **mandatory**
	* You can omit the colon if you don't want repeating subdivisions

Similarly the "radial subdivisions" control how the main concentric circles are divided into subcircles.  
Use the `grid-rsubdiv/grsub SUB1 ...` command.  

# Saving / Loading / Exporting
cf commands `s/save`, `load/lo`, `ls-saves`, `quit/q`, `outline`
TODO (say more)

# Configuration 
TODO

# TODO
saving/loading/exporting
conf file (mention rc)

Index and links
note about layout problems

