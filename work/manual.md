# Basics
Place your left hand on the home row (ASDF), and use your mouse with your right hand.

## Using the Menu
The botton area of the screen displays a list of all currently available menu actions (e.g. `D: Draw Shape`), which are always activated by hitting the corresponding key on the keyboard.  
After triggering an action, the mappings will change to more contextually relevant sub-actions.  
Use `X` or `SPACE` to come back to the start of the menu. (This will also cancel currently unifinished actions)  

The bottom 4 actions (`Camera`, `Menu Top`, `Command` and `Rewind`) are "pinned", and are available form anywhere in the menu.  

Triggering an action in the menu will often change the behavior of the mouse, and/or display a **hint at the bottom of screen**.  
For example after `D: Draw Shape`/`S: New Segment`, left-clicking on 2 points will draw a segment between them.  

## The Commandline
Some things are acheived through the command-line (i.e. by literally typing commands).  
Use `C: Command`, to enter the command-line and start typing a commands. A green command prompt will appear.  
To quit the command-line use `Ctrl-C` or use `Enter` when the prompt is empty (no text was typed since the last command).  
The cursor is always at the end of the line and you cannot navigate with the arrows (or the mouse).  

See list of available commands (look first at `help` (TODO link) and `ls-cmd` (TODO link)). [TODO link]  

Available shortcuts:
* `Ctrl-U`: erase current line
* `Ctrl-C`: cancel and close commandline
* `Ctrl-W` or `Ctrl-BackSpace`: erase last word

## Notes

* Whenever the mouse-wheel is not doing something else, you can zoom the view by scrolling.
* Nails (Points on shapes) are snappy. i.e. clicks close enough to them are treated as being **exactly** on them

* To move the view, go to `Z: Camera` and right-click twice: once to grab, once to release.
* Leaving view adjustement (with left-click) will resume whatever you were doing.

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

Note: reminders for the above will be displayed will be displayed at the bottom of the screen when you select a shape type.

# Drawing Weaves (and working with colors)
The colorful strings between are nails are organized in "weaves".
Go to `F: Draw Weave` to start creating weaves.

## Creating Weaves
To create a new weave: 
* left-click a nail on any shape to define the first attach point 
* left-click another nail on another (or the same) shape to define the second attach point 
* left-click a third time on any nail on the same shape where the second attach point is to extend the weave.
* **Note:** For the first 2 attach points, if you click on a nail that is at the intersection of several shapes, you will need to choose what shape you want to use by clicking another nail on it.

A colorful string should be drawn between the first 2 attach points, and between every 2 points after them on their respective shapes until the third attach point is reached, or the first shape runs out of nails.

For any 3 attach points, there are up to 4 possible weaves depending on:
* The direction we're going in on the first shape. (swap with `A: Invert dir`)
* For loopy shapes, whether we're going clockwise or not. (swap with `S: Invert Spin`)
Right-clicking will go through all 4 possibilities so you can choose.

Some commands affect the behavior when drawing weaves:
* `weaveback/wb`: toggles `weaveback` (on by default). If `weaveback` is enabled, a second set of colorful strings will appear to connect the previous set, as if all the lines came from a single string that wraps around the nails.
* `weavity/wy inc1 inc2`: set the "weavity" (1 -1 by default). which allow skipping some nails. (eg if the weavity is 2 1, a nail will be skipped every time when finding the "next" nail on the first shape).

## Using Colors
For drawing weaves you use any of 8 different colors associated with one of the `QWERASDF` keyboard keys.  
To select to apply when confirming a new weave, use `E: Select Color`, then hit the key corresponding to the color you want to use.  

To customize a color use `W: Color Picker`. When you modify a color this way, the weaves that were drawn using this color will also be modified (in real time).  
In the color picker:
* use of the `QWERASDF` keys to select the color you want to modify.
* left-click the big rainbow to choose the color to apply for this key.
* repeat for every color you want to modify.
* Use right-click when you're done. 





