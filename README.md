# How to install

- The main branch always contains the most up-to-date version. You can always download the main branch, install the package in `requirements.txt` and run `msiAlign.py`;
- For the latest binary you can always get from [here](https://github.com/weimin-liu/msiAlign/releases/latest). For now, you will get warning that it's a trojan and will be deleted, it's due to an issue with pyinstaller (e.g. reported [here](https://stackoverflow.com/questions/43777106/program-made-with-pyinstaller-now-seen-as-a-trojan-horse-by-avg), [here](https://stackoverflow.com/questions/64788656/exe-file-made-with-pyinstaller-being-reported-as-a-virus-threat-by-windows-defen) and [here](https://github.com/pyinstaller/pyinstaller/issues/5854)). It's **False Positive**, and you need to allow it to run in your antivirus program. It might be solved in later versions...

# Known bugs (ticked means fixed):

- [x] Special vertical lines (e.g. sediment start, scale lines) may not be properly deleted 
- [x] If the images are moved after the teaching points are added, the teaching points coordinates are not properly updated
- [x] When duplicate images are added, the image will be re-added to the canvas instead of popping up a warning

# How to use

## For those in a hurry

### Add images:
Use File - Add images to add images to the canvas. You will be asked if the added image is xray (x) or linescan (l) or msi image (m). The first two labels (x and l) are important for the program to work properly and can only be linked to one image each, the m label is not used at the moment. 

### Organize images:
Put the images in the right place by dragging them around and resize them by dragging the corners. You can ctrl+left click to add vertical lines to the canvas to help you align the images.
Avoid overlapping the linescan or xray images with the MSI scan image.

### Calculate cm/pixel: 
Add two vertical lines on the canvas, for example, at the 1cm and 2cm marks on the line scan image. Then, right click on the vertical lines two set them as "scale lines", and then in menu, click Calc - cm/Px, the program will ask you for the distance between the two lines in cm, and then it will calculate the cm/pixel ratio for the canvas.

### Mark sediment start:
Add another vertical line at the start of the sediment. Right click on the line and select "Sediment start".

### Mark the teaching points:
Add teaching points by shift+left clicking on the canvas. The program will automatically calculate the distance from the sediment start to the teaching point.

### Create Metadata Database
Use "File>Crawl Metadata" and navigate to the directory containing the imaging folders (those that end on .i)

### Attach  database
Click File - Attach database and select the database file produced by the above step.

### Get the transformed coordinates:
Click Calc - Machine to Real World, you will be asked if you want to manually or automatically pair the teaching points
- Manually: 
  - Label: if you want to manually pair the teaching points, you need to first label all the teaching points with integer values (right click on the teaching point and select "Label"). Or, to save some time, you can use `Dev` -> `Auto add TP labels` to automatically add integer labels starting from 0 to all teaching points.
  - Pair: then, you need to pair the teaching points when asked by the program. The input should like below. Basically, each line is a pair of teaching points, and they are seperated by whitespace.
  ![Screenshot 2024-03-14 at 14.21.28.png](imgs%2FScreenshot%202024-03-14%20at%2014.21.28.png)
  - Calculate: click `Submit` button and the program will calculate the transformation matrix and the transformed coordinates, the results will be saved in the database. If you save the workspace now, the paired teaching points will also be saved, and next time you can just click fill to re-fill the pairs.
- Automatically:
  - The program will automatically pair the teaching points in a clockwise order, and calculate the transformation matrix and the transformed coordinates.

## Useful functions:
### Save and load the canvas:
you can save and load the canvas by clicking File - Save Workspace and File - Load Workspace. The workspace file is a json file that contains the image paths, the cm/pixel ratio, the scale lines, the sediment start line, the teaching points.

### View the coordinates of the teaching points:
You can view the coordinates of the teaching points by clicking View - Update TP View. The coordinates will be shown on the side of the canvas.

## Why is it not working?

### I can't drag the images around:
- Make sure the image file names don't contain spaces. It's best that the file names don't contain any special characters except underscore.

### For `Calc depth profile`:
- The exported DA txt should be named exactly the same as the spectrum data, for example, if the spectrum data is named `xxxx.d`. The DA txt should be named `xxxx.d.txt`.

