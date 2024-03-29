# How to use

## For those in a hurry

### Add images:
Use File - Add images to add images to the canvas. You will be asked if the added image is xray (x) or linescan (l) or msi image (m). The first two labels (x and l) are important for the program to work properly and can only be linked to one image each, the m label is not used at the moment. 

### Organize images:
Put the images in the right place by dragging them around and resize them by dragging the corners. You can ctrl+left click to add vertical lines to the canvas to help you align the images.

### Calculate cm/pixel: 
Add two vertical lines on the canvas, for example, at the 1cm and 2cm marks on the line scan image. Then, right click on the vertical lines two set them as "scale lines", and then in menu, click Calc - cm/Px, the program will ask you for the distance between the two lines in cm, and then it will calculate the cm/pixel ratio for the canvas.

### Mark sediment start:
Add another vertical line at the start of the sediment. Right click on the line and select "Sediment start".

### Mark the teaching points:
Add teaching points by shift+left clicking on the canvas. The program will automatically calculate the distance from the sediment start to the teaching point.

### Attach the database
Click File - Attach database and select the database file produced by `metadata_crawler.py`. 

### Convert the teaching points coordinates from pixel to machine coordinates:
Click Calc - MSI Machine Coord

### Calculate the transformation matrix between three kinds of images:
Click Calc - Calc Transformation Matrix

### Get the transformed coordinates of the teaching points:
Click Calc - Machine to Real World, the results will be saved in the attached database file.

## Useful functions:
### Save and load the canvas:
you can save and load the canvas by clicking File - Save Workspace and File - Load Workspace. The workspace file is a json file that contains the image paths, the cm/pixel ratio, the scale lines, the sediment start line, the teaching points.

### View the coordinates of the teaching points:
You can view the coordinates of the teaching points by clicking View - Update TP View. The coordinates will be shown on the side of the canvas.