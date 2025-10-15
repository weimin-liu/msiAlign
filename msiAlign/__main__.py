import json
import os
import re
import sqlite3
import sys
import tkinter as tk
from tkinter import filedialog
from tkinter import simpledialog, messagebox

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from msiAlign.func import CorSolver
from msiAlign.menubar import MenuBar
from msiAlign.objects import LoadedImage, VerticalLine, MsiImage, TeachableImage
from msiAlign.rclick import RightClickOnLine, RightClickOnImage, RightClickOnTeachingPoint


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1200x800")
        self.canvas = None
        self.right_click_on_tp = None
        self.right_click_on_image = None
        self.right_click_on_line = None
        self.title('Ctrl+O to add images, Shift+click to add teaching points, Ctrl+click to add rulers')
        self.items = {}
        self.create_canvas()
        self.xrf_folder = None
        self.database_path = None
        self.pair_tp_str = None

        self.scale_line = []
        self.sediment_start = None

        self.cm_per_pixel = None
        self.save_attrs = [
            'cm_per_pixel', 'database_path', 'pair_tp_str', 'sediment_start', 'scale_line'
        ]
        self.calculation_handler = CalculationHandler(self)
        self.dev_ops_handler = DevOpsHandler(self)
        self.xrf_handler = XRFHandler(self)
        self.menu = MenuBar(self)

        self.create_right_click_op()

    def create_right_click_op(self):
        self.right_click_on_line = RightClickOnLine(self)
        self.right_click_on_image = RightClickOnImage(self)
        self.right_click_on_tp = RightClickOnTeachingPoint(self)

    def create_canvas(self):
        canvas_width = 1000
        canvas_height = 1000
        # Create a frame for the canvas and scrollbars
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_frame, width=canvas_width, height=canvas_height, bg='white',
                                scrollregion=(0, 0, 5000, 5000))
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Create horizontal and vertical scrollbars
        h_scroll = tk.Scrollbar(self.canvas, orient='horizontal', command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill='x')
        v_scroll = tk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill='y')
        # bind the mousewheel event to the canvas
        # Configure the canvas to use the scrollbars
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self.horizontal_mousewheel)

    def on_mousewheel(self, event):
        try:
            # For windows and MacOS
            # if it's macos
            if sys.platform == "darwin":
                self.canvas.yview_scroll(event.delta, "units")
            # else it's windows
            elif sys.platform == "win32":
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except AttributeError:
            raise AttributeError("The mousewheel event is not supported on this platform")

    def horizontal_mousewheel(self, event):
        try:
            # For windows and MacOS
            self.canvas.xview_scroll(event.delta, "units")
        except AttributeError:
            raise AttributeError("The mousewheel event is not supported on this platform")

    def on_drag_start(self, item, event):
        """Function to handle dragging"""
        # Get the coordinates of the image
        x1, y1, x2, y2 = self.canvas.bbox(item)

        # create a temporary variable to store the old width
        self._old_width = self.items[item].thumbnail.width

        # calculate the offset
        _drag_offset_x = self.canvas.canvasx(event.x) - x1
        _drag_offset_y = self.canvas.canvasy(event.y) - y1
        # Create a rectangle around the image
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="blue", tags="rect")

        # Calculate the corner threshold as a percentage of the image's width and height
        corner_threshold_x = (x2 - x1) * 0.1
        corner_threshold_y = (y2 - y1) * 0.1

        # if the mouse is near the bottom-right corner, start resizing
        if (abs(x2 - self.canvas.canvasx(event.x)) < corner_threshold_x
                and abs(y2 - self.canvas.canvasy(event.y)) < corner_threshold_y):
            self.canvas.bind("<B1-Motion>", lambda e: self.on_resize(e, item))
            self.canvas.bind("<ButtonRelease-1>", lambda e: self.on_resize_stop(e, item))

        else:
            self.canvas.bind("<B1-Motion>", lambda e: self.on_drag_move(e, item, _drag_offset_x, _drag_offset_y))
            self.canvas.bind("<ButtonRelease-1>", lambda e: self.on_drag_stop(e, item))

    def on_drag_move(self, event, item, _drag_offset_x, _drag_offset_y):
        """move the item to the new position"""
        x, y = self.canvas.canvasx(event.x) - _drag_offset_x, self.canvas.canvasy(event.y) - _drag_offset_y
        self.canvas.coords(item, x, y)

    def on_drag_stop(self, event, item):
        """Stop dragging the image"""
        # record the origin offset of the image
        offset_x = self.canvas.coords(item)[0] - self.items[item].origin[0]
        offset_y = self.canvas.coords(item)[1] - self.items[item].origin[1]
        # record the new position of the image
        x, y = self.canvas.coords(item)
        self.items[item].origin = (x, y)
        # remove the rectangle from the canvas
        self.canvas.delete('rect')
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        # update the teaching points
        if isinstance(self.items[item], TeachableImage):
            self.items[item].update_teaching_points(self, offset_x, offset_y)

    def on_resize(self, event, item):
        """Resize the image based on mouse position"""
        x1, y1, x2, y2 = self.canvas.bbox(item)
        new_width = self.canvas.canvasx(event.x) - x1
        # Prevent the image from being too small
        new_width = max(new_width, 100)
        # get the original PIL image
        image = self.items[item].thumbnail
        # calculate the aspect ratio of the original image
        aspect_ratio = image.width / image.height
        # calculate the new height based on the aspect ratio
        new_height = new_width / aspect_ratio
        # resize the image by creating a new image with the new dimensions
        self.items[item].resize((new_width, new_height))

        self.canvas.itemconfig(item, image=self.items[item].tk_img)
        # TODO: an error will be raised here if there are teaching points on the image, no need
        # to panic. This is because the teaching points have the same tag as the image, so they
        # are also be configured, but they cannot be configured with the image, so the error is raised

    def on_resize_stop(self, event, item):
        """Stop resizing the image"""
        self.resizing = False
        # remove the rectangle from the canvas
        self.canvas.delete('rect')
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        if isinstance(self.items[item], TeachableImage):
            self.items[item].update_teaching_points_on_resize(self, self.items[item].origin,
                                                              self.items[item].thumbnail.width / self._old_width)

    def add_vertical_line(self, event):
        """draw a ruler on the canvas when ctrl-left-click is pressed, and calculate the scale"""
        vl = VerticalLine((self.canvas.canvasx(event.x), 0))
        self.items[vl.tag] = vl
        vl.create_on_canvas(self)

        # calculate the pixel distance between this ruler and sediment_start
        if self.sediment_start is not None and self.cm_per_pixel is not None:
            pixel_distance = self.canvas.coords(self.sediment_start)[0] - self.canvas.canvasx(event.x)
            real_distance = pixel_distance * self.cm_per_pixel
            vl.add_depth_text(self, f"{abs(real_distance):.2f}")

    def find_clicked_image(self, event):
        # TODO: could be optimized by using addtag_withtag when creating the images and the items
        clicked_images = []
        for k, v in self.items.items():
            if isinstance(v, LoadedImage):
                x1, y1, x2, y2 = self.canvas.bbox(v.tag)
                if x1 <= self.canvas.canvasx(event.x) <= x2 and y1 <= self.canvas.canvasy(event.y) <= y2:
                    clicked_images.append(v)

        if len(clicked_images) == 1:
            return clicked_images[0]
        elif len(clicked_images) > 1:
            # when images are overlapping, find the front image
            # first call find_all to get the current order of the images
            current_order = self.canvas.find_all()
            # sort the clicked images based on the current order
            clicked_images = sorted(clicked_images,
                                    key=lambda x: current_order.index(self.canvas.find_withtag(x.tag)[0]))
            return clicked_images[-1]
        else:
            return None

    def bind_events_to_loaded_images(self, loaded_image):
        """Bind events to the loaded images"""
        self.canvas.tag_bind(f"{loaded_image.tag}", "<Button-1>",
                             lambda e, item=f"{loaded_image.tag}": self.on_drag_start(item, e))
        # bind ctrl-left-click to add a ruler
        self.canvas.tag_bind(f"{loaded_image.tag}", "<Control-Button-1>", self.add_vertical_line)
        # bind shift-left-click to add a teaching point
        self.canvas.tag_bind(f"{loaded_image.tag}", "<Shift-Button-1>",
                             lambda e: self.add_teaching_point(e))
        # bind right-click event to the image
        if sys.platform == "darwin":
            self.canvas.tag_bind(f"{loaded_image.tag}",
                                 "<Button-2>",
                                 lambda e, item=f"{loaded_image.tag}": self.right_click_on_image.show_menu(e, item))
        elif sys.platform == "win32":
            self.canvas.tag_bind(f"{loaded_image.tag}",
                                 "<Button-3>",
                                 lambda e, item=f"{loaded_image.tag}": self.right_click_on_image.show_menu(e, item))
        else:
            raise ValueError("The platform is not supported")

    def add_tp_labels(self):
        """Add labels for all the teaching points"""
        label_idx = 0
        for k, v in self.items.items():
            try:
                for i, tp in v.teaching_points.items():
                    # append label to the teaching_points dictionary
                    v.teaching_points[i] = list(v.teaching_points[i])
                    try:
                        v.teaching_points[i][3] = label_idx
                    except IndexError:
                        v.teaching_points[i].append(label_idx)
                    v.teaching_points[i] = tuple(v.teaching_points[i])

                    try:
                        # pass the label to teaching point px coords
                        v.teaching_points_px_coords[i] = list(v.teaching_points_px_coords[i])
                        try:
                            v.teaching_points_px_coords[i][3] = label_idx
                        except IndexError:
                            v.teaching_points_px_coords[i].append(label_idx)
                        v.teaching_points_px_coords[i] = tuple(v.teaching_points_px_coords[i])
                    except AttributeError:
                        pass
                    except IndexError:
                        messagebox.showerror("Error", "Something went wrong when adding labels to teaching points")
                    label_idx += 1

            except AttributeError:
                pass
        # show the labels
        self.show_tp_labels()

    def show_tp_labels(self):
        """ display the labels of the teaching points on the canvas"""
        for k, v in self.items.items():
            if isinstance(v, TeachableImage):
                v.show_tp_labels(self)

    def hide_tp_labels(self):
        """delete all the text items on the canvas labeled 'tp_labels'"""
        self.canvas.delete('tp_labels')

    def fill_tps_str(self):
        try:
            return self.pair_tp_str
        except AttributeError:
            return ""

    def bind_events_to_vertical_lines(self, vertical_line):
        """Bind events to the vertical lines"""
        if sys.platform == "darwin":
            self.canvas.tag_bind(f"{vertical_line.tag}",
                                 "<Button-2>",
                                 lambda e, item=f"{vertical_line.tag}": self.right_click_on_line.show_menu(e, item))
        elif sys.platform == "win32":
            self.canvas.tag_bind(f"{vertical_line.tag}",
                                 "<Button-3>",
                                 lambda e, item=f"{vertical_line.tag}": self.right_click_on_line.show_menu(e, item))
        else:
            raise ValueError("The platform is not supported")
        # bind shift-left-click to add a teaching point
        self.canvas.tag_bind(f"{vertical_line.tag}", "<Shift-Button-1>", self.add_teaching_point)

    def add_teaching_point(self, event):
        """Add a teaching point to the canvas"""
        clicked_image = self.find_clicked_image(event)
        if not isinstance(clicked_image, TeachableImage) and not isinstance(clicked_image, MsiImage):
            messagebox.showerror("Wrong image", "Click a Teachable image to add a teaching point")
            return
        if clicked_image is not None:
            clicked_image.add_teaching_point(event, self)

    def add_metadata(self):
        """Add metadata to the app"""
        # note that the metadata needed to be added to the app after all msi images are loaded
        # ask the user if all the msi images are loaded
        userchoice = messagebox.askokcancel(
            "Add Metadata",
            "All the MSI images need to be loaded before adding metadata, continue adding metadata?",
            icon='warning'
        )
        if not userchoice:
            return
        file_path = filedialog.askopenfilename(title="Select a database file", filetypes=[("SQLite files", "*.db")])
        if file_path:
            self.database_path = file_path
        else:
            messagebox.showerror("No file path is given")
        # connect to the sqlite database
        import sqlite3
        conn = sqlite3.connect(file_path)
        c = conn.cursor()
        # get the image name, px_rect, and msi_rect
        c.execute('SELECT msi_img_file_name, px_rect, msi_rect FROM metadata')
        data = c.fetchall()
        count = 0
        for row in data:
            im_name, px_rect, msi_rect = row
            # attach the metadata to the corresponding image
            try:
                self.items[im_name.replace(' ','_')].px_rect = eval(px_rect)
                self.items[im_name.replace(' ','_')].msi_rect = eval(msi_rect)
                count += 1
            except KeyError:
                pass
        conn.close()
        # create a popup window to show the process is done, and ok button to close the window
        messagebox.showinfo("Success", f"{count} images have been added with metadata")

    def use_as_ref_to_resize(self, item):
        """use the selected image as the reference to resize other images"""
        ref_width = self.items[item].thumbnail.width
        for k, v in self.items.items():
            if isinstance(v, MsiImage):
                scale_factor = ref_width / v.thumbnail.width
                self.items[k].enlarge(scale_factor)
                try:
                    self.canvas.itemconfig(k, image=self.items[k].tk_img)
                except tk.TclError:
                    pass

    def save_layout(self, event=None):
        """Save the layout of the canvas"""
        self.save(layout_only=True)

    def save(self, event=None, layout_only=False):
        """Save the current state of the canvas"""
        file_path = filedialog.asksaveasfilename(title="Save workspace",
                                                 defaultextension=".json",
                                                 filetypes=[("JSON", "*.json")])
        if not file_path:
            return  # User cancelled the save dialog
        data_to_save = {}

        # Save the attributes automatically
        for attr in self.save_attrs:
            data_to_save[attr] = getattr(self, attr, None)

        # Save items
        data_to_save["items"] = []
        for k, v in self.items.items():
            if not layout_only or not isinstance(v, MsiImage):
                data_to_save["items"].append(v.to_json())

        with open(file_path, "w") as f:
            json.dump(data_to_save, f)

    def load(self, event=None):
        """Load the state of the canvas"""
        file_path = filedialog.askopenfilename(title="Select a workspace file", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return  # User cancelled the load dialog
        with open(file_path, "r") as f:
            data = json.load(f)
            # Reset the canvas
            self.dev_ops_handler.reset()

            # Load the attributes automatically
            for attr in self.save_attrs:
                setattr(self, attr, data.get(attr, None))

            # Recreate canvas text for cm_per_pixel
            if self.cm_per_pixel is not None:
                text = tk.Text(self.canvas, height=1, width=20)
                text.insert(tk.END, f"1cm = {int(1 / self.cm_per_pixel)} pixel")
                text.config(state="disabled")
                self.canvas.create_window(100, 100, window=text, tags="cm_per_px_text")

            # Load items
            for item in data.get("items", []):
                if "MsiImage" in item["type"]:
                    loaded_image = MsiImage.from_json(item, self)
                    self.items[loaded_image.tag] = loaded_image
                elif "TeachableImage" in item["type"]:
                    loaded_image = TeachableImage.from_json(item, self)
                    self.items[loaded_image.tag] = loaded_image
                elif item["type"] == "VerticalLine":
                    vertical_line = VerticalLine.from_json(item, self)
                    self.items[vertical_line.tag] = vertical_line
                    self.bind_events_to_vertical_lines(vertical_line)

            # Reconfigure scale lines and sediment start if they exist
            if self.scale_line:
                # Ensure that scale_line contains items
                if len(self.scale_line) >= 2:
                    self.canvas.itemconfig(self.scale_line[0], fill="blue")
                    self.canvas.itemconfig(self.scale_line[1], fill="blue")
            if self.sediment_start:
                self.canvas.itemconfig(self.sediment_start, fill="green")


    def find_wildcard(self, wildcard):
        """find the tag with the wildcard"""
        items = self.canvas.find_all()
        matched_items = []
        for item in items:
            if wildcard in self.canvas.gettags(item)[0]:
                matched_items.append(self.canvas.gettags(item))
        return matched_items

    def main(self):
        self.mainloop()

class DevOpsHandler:
    def __init__(self, app):
        self.app = app

    def set_tp_size(self):
        """set the size of the teaching points"""
        size = simpledialog.askinteger("Input", "Enter the size of the teaching points", initialvalue=5)
        size = size if size is not None else 5
        for k, v in self.app.items.items():
            if isinstance(v, TeachableImage):
                v.tp_size = size

    def reset(self):
        userchoice=tk.messagebox.showwarning("Warning", "This will reset the canvas, are you sure?")
        if userchoice == 'yes':
            # reset the canvas
            self.app.canvas.delete("all")
            self.app.items = {}
            self.app.cm_per_pixel = None
            self.app.database_path = None
            self.app.pair_tp_str = None
            self.app.scale_line = []
            self.app.sediment_start = None
            self.app.pair_tp_str = None
            self.app.solvers_xray = {}
            self.app.solvers_depth = {}
        else:
            pass

    def export_tps(self):
        """Export the teaching points to a json file"""
        file_path = filedialog.asksaveasfilename(title="Export Teaching Points",
                                                 defaultextension=".json",
                                                 filetypes=[("JSON files", "*.json")])
        if file_path:
            data_to_save = "img;x;y;d\n"
            for k, v in self.app.items.items():
                if hasattr(v, "teaching_points"):
                    for k, tp in v.teaching_points.items():
                        data_to_save += f"{v.tag};{tp[0]};{tp[1]};{tp[2]}\n"
            with open(file_path, "w") as f:
                f.write(data_to_save)
            messagebox.showinfo("Export Teaching Points", f"Teaching points have been exported to {file_path}")
        else:
            messagebox.showinfo("Export Teaching Points", "No file path is given")
            return

    def reset_tp(self):
        """
        Reset the teaching points
        """
        # remove all the teaching points from the canvas
        for k, v in self.app.items.items():
            if isinstance(v, TeachableImage):
                if v.teaching_points is not None:
                    v.teaching_points = {}
                if hasattr(v, "teaching_points_updated"):
                    v.teaching_points_updated = False
        # hard remove all the teaching points oval from the canvas with tag including 'tp_'
        try:
            # list all tags
            tps = self.app.find_wildcard('tp_')
            for tp in tps:
                try:
                    self.app.canvas.delete(tp[0])
                except IndexError:
                    self.app.canvas.delete(tp)
        except AttributeError:
            pass
        messagebox.showinfo("Done", "All the teaching points are removed")

        # clear the tree view
        try:
            self.app.tree.delete(*self.app.tree.get_children())
        except AttributeError:
            pass

    def calc_depth_for_all_tps(self):
        """calculate the depth for all the teaching points"""
        if self.app.sediment_start is None:
            messagebox.showerror("Error", "No sediment start is found")
            return
        if self.app.cm_per_pixel is None:
            messagebox.showerror("Error", "No cm_per_pixel is found")
            return
        user_choice1 = messagebox.askyesno("Warning",
                                           "This will overwrite the current depth of the teaching points,"
                                           " are you sure?")
        user_choice2 = messagebox.askyesno("Warning",
                                           "If you have moved the xray images after setting the teaching points, "
                                           "the depth will be incorrect, are you sure?")

        if user_choice1 and user_choice2:
            for k, v in self.app.items.items():
                if isinstance(v, TeachableImage):
                    try:
                        for px_coords, values in v.teaching_points.items():
                            depth = abs(self.app.canvas.coords(self.app.sediment_start)[0] - px_coords[0]) * self.app.cm_per_pixel
                            _tmp = list(values)
                            _tmp[2] = depth
                            v.teaching_points[px_coords] = tuple(_tmp)
                    except Exception as e:
                        messagebox.showerror("Error", f"Error: {e}")
                    try:
                        for px_coords, values in v.teaching_points_px_coords.items():
                            depth = abs(self.app.canvas.coords(self.app.sediment_start)[0] - px_coords[0]) * self.app.cm_per_pixel
                            _tmp = list(values)
                            _tmp[2] = depth
                            v.teaching_points_px_coords[px_coords] = tuple(_tmp)
                    except AttributeError:
                        pass

            messagebox.showinfo("Done", "The depth for all the teaching points are calculated")

    def lock_all(self):
        # invoke lock_image method for all the images
        for k, v in self.app.items.items():
            if isinstance(v, LoadedImage):
                self.app.right_click_on_image.lock_image(k)
        messagebox.showinfo("Done", "All the images are locked")

class CalculationHandler:
    def __init__(self, app):
        self.app = app

    def calc_cm_per_px(self):
        # get the two vertical scale lines
        if len(self.app.scale_line) < 2:
            messagebox.showerror("Error", "You need to draw two vertical lines to calculate the scale")
            raise ValueError("You need to draw two vertical lines to calculate the scale")
        elif len(self.app.scale_line) > 2:
            messagebox.showerror("Error", f"You have drawn more than two vertical lines:{self.app.scale_line} ")
            raise ValueError("You have drawn more than two vertical lines")
        else:
            pixel_distance = abs(
                self.app.canvas.coords(self.app.scale_line[1])[0] - self.app.canvas.coords(self.app.scale_line[0])[0])
            real_distance = simpledialog.askfloat("Real Distance", "Real Distance (cm):")
            self.app.cm_per_pixel = real_distance / pixel_distance
            text = tk.Text(self.app.canvas, height=1, width=20)
            text.insert(tk.END, f"1cm = {int(1 / self.app.cm_per_pixel)} pixel")
            text.config(state="disabled")
            self.app.canvas.create_window(100, 100, window=text, tags="cm_per_px_text")

    def calc_msi_machine_coordinate(self):
        for k, v in self.app.items.items():
            if isinstance(v, MsiImage):
                try:
                    v.update_tp_coords(self.app.database_path)
                except AttributeError:
                    messagebox.showerror("Error", "No database path is found")
                    return

    def machine_to_real_world(self):
        """apply the transformation to the msi teaching points"""
        # ask for the sqlite file to read the metadata
        if self.app.database_path is None:
            self.app.add_metadata()
        # connect to the sqlite database
        file_path = self.app.database_path
        if file_path:
            # connect to the sqlite database
            conn = sqlite3.connect(file_path)
            c = conn.cursor()
            try:
                # check if the transformation table exists
                c.execute('SELECT * FROM transformation')
                # purge the transformation table
                c.execute('DELETE FROM transformation')
                # delete the transformation table
                c.execute('DROP TABLE transformation')
                conn.commit()
            except sqlite3.OperationalError:
                pass
            # create a transformation table with metadata(spec_id) as the reference key
            try:
                c.execute(
                    'CREATE TABLE transformation (spec_id INTEGER, msi_img_file_name TEXT, spot_array BLOB, xray_array BLOB, linescan_array BLOB, FOREIGN KEY(spec_id) REFERENCES metadata(spec_id))')
                conn.commit()
            except sqlite3.OperationalError:
                pass
            # read all the spotname from metadata table and convert them to array
            c.execute('SELECT spec_id, msi_img_file_name, spot_name FROM metadata')
            data = c.fetchall()
            assert len(data) > 0, "No data is found in the metadata table"
            for row in data:
                spec_id, im_name, spot_name = row
                spec_id = int(spec_id)
                spot_name = eval(spot_name)
                # apply the transformation to the spot_name
                spot_name = [re.findall(r'X(\d+)Y(\d+)', s) for s in spot_name]
                # flatten the list
                spot_name = [item for sublist in spot_name for item in sublist]
                # convert to an array
                spot_name = np.array(spot_name)
                # conver the spotname to int
                spot_name = spot_name.astype(int)
                # write the spotnames to the transformation table as a blob
                c.execute('INSERT INTO transformation (spec_id, msi_img_file_name, spot_array) VALUES (?, ?, ?)',
                          (spec_id, im_name, spot_name.tobytes()))
                conn.commit()
            c.execute('SELECT spec_id, msi_img_file_name, spot_array FROM transformation')
            data = c.fetchall()
            for row in data:
                spec_id, im_name, spot_array = row
                spec_id = int(spec_id)
                spot_array = np.frombuffer(spot_array, dtype=int).reshape(-1, 2)
                # apply the transformation to the spot_array
                if im_name in self.app.solvers_xray.keys() or im_name.replace(' ', '_') in self.app.solvers_xray.keys():
                    xray_array = self.app.solvers_xray[im_name.replace(' ','_')].transform(spot_array)
                    xray_array_dtype = xray_array.dtype
                    # store_blob_info(conn, 'xray_array', xray_array_dtype, xray_array.shape)
                    xray_array_shape = xray_array.shape
                    linescan_array = self.app.solvers_depth[im_name.replace(' ', '_')].transform(spot_array)
                    # line_scan_dtype = linescan_array.dtype
                    # linescan_array_shape = linescan_array.shape
                    # store_blob_info(conn, 'linescan_array', line_scan_dtype, linescan_array_shape)
                    c.execute('UPDATE transformation SET xray_array = ? WHERE spec_id = ?',
                              (xray_array.tobytes(), spec_id))
                    c.execute('UPDATE transformation SET linescan_array = ? WHERE spec_id = ?',
                              (linescan_array.tobytes(), spec_id))
            conn.commit()
            conn.close()
        else:
            messagebox.showerror("No file path is given")

        # create a popup window to show the process is done, and ok button to close the window
        messagebox.showinfo("Done", "The transformation is applied to the MSI coords")

    def pair_tps(self, str1, msi=False, xrf=False):
        self.app.pair_tp_str = str1
        # remove the leading and trailing white spaces
        str1 = str1.strip()
        # convert the input string to a list of tuples
        str1 = str1.split('\n')
        str1 = [s.split(' ') for s in str1]

        str1 = [[int(x) for x in s] for s in str1]
        paired_tps = str1
        # get all teaching points from xray:
        for k, v in self.app.items.items():
            if isinstance(v, TeachableImage) and not isinstance(v, MsiImage):
                xray_tps = v.label_indexed_teaching_points
                break
        # get all their labels
        xray_tp_labels = list(xray_tps.keys())
        # convert self.app.paired_tps to a dictionary using xray_tp_labels as the values
        paired_tps_dict = {}
        for i, v in enumerate(paired_tps):
            if v[0] in xray_tp_labels:
                paired_tps_dict[v[1]] = v[0]
            elif v[1] in xray_tp_labels:
                paired_tps_dict[v[0]] = v[1]
            else:
                continue

        self.app.solvers_xray = {}
        self.app.solvers_depth = {}

        for k, v in self.app.items.items():
            if isinstance(v, MsiImage) or isinstance(v, TeachableImage):
                try:
                    msi_tps = v.label_indexed_teaching_points
                    # find the teaching points that have the paired label in xray_tps
                    partial_xray_tps = {}
                    for msi_tp_label in msi_tps.keys():
                        if msi_tp_label in paired_tps_dict.keys():
                            partial_xray_tps[msi_tp_label] = xray_tps[paired_tps_dict[msi_tp_label]]
                    self.app.solvers_xray[k] = CorSolver()
                    self.app.solvers_xray[k].fit(np.array(list(msi_tps.values()))[:, 0:2],
                                             np.array(list(partial_xray_tps.values()))[:, 0:2])
                    self.app.solvers_depth[k] = CorSolver()
                    self.app.solvers_depth[k].fit(np.array(list(msi_tps.values()))[:, 0:2],
                                              np.array(list(partial_xray_tps.values()))[:, [2, 1]])
                except Exception as e:
                    print(e)
                    pass
        if msi:
            self.machine_to_real_world()

        if xrf:
            self.app.xrf_handler.prepare_for_xrf()

    def calc_msi(self):
        # test if metadata is added
        if self.app.database_path is None:
            # create a messagebox to show that the metadata is not added yet
            userchoice = messagebox.askokcancel(
                "Metadata is not added yet",
                "Do you want to add metadata now?",
                icon='warning'
            )
            if userchoice:
                self.app.add_metadata()
            else:
                return

        # calculate the MSI machine coordinate

        self.calc_msi_machine_coordinate()
        # create a messagebox to ask if the user wants to pair the teaching points automatically or manually
        self.app.menu.pair_tps_ui(msi=True)


class XRFHandler:
    def __init__(self, app):
        self.app = app
        self.xrf_folder = None
        self.elements = None

    def set_xrf_folder(self):
        """set the folder to store the xrf images"""
        folder_path = filedialog.askdirectory(title="Select a folder that contains all the XRF data")
        if folder_path:
            self.xrf_folder = folder_path
            self.read_all_elements()
        else:
            messagebox.showerror("No folder path is given")


    def read_all_elements(self):
        """read all the elements from the xrf images"""
        if self.xrf_folder is None:
            self.set_xrf_folder()
        if self.xrf_folder:
            # list all the folders in the xrf folder
            xrf_folders = [f for f in os.listdir(self.xrf_folder) if os.path.isdir(os.path.join(self.xrf_folder, f))]
            self.elements = {}
            for a_folder in xrf_folders:
                # get all the xrf images in the folder (.txt files without 'Video' in the name)
                xrf_files = [f for f in os.listdir(os.path.join(
                    self.xrf_folder, a_folder
                )) if f.endswith('.txt')]
                if len(xrf_files) == 0:
                    # ignore empty folders
                    continue
                element = {}
                # read all the elements from the xrf images
                # find the changing parts and the common parts of all names
                common_part = os.path.commonprefix(xrf_files)
                # safely ignore the folder if there is no common part
                if common_part == '':
                    messagebox.showwarning(
                        title='Warning',
                        message=f'No common part found in the txt files in the folder {a_folder}, skipping the folder'
                    )
                    continue
                changing_parts = [f.replace(common_part, '').replace('.txt', '') for f in xrf_files]
                for i, f in enumerate(xrf_files):
                    try:
                        element[changing_parts[i]] = pd.read_csv(os.path.join(self.xrf_folder,a_folder, f), sep=';',header=None)
                    except Exception as e:
                        print(e)
                        pass # sometimes there are corrupted txt files in the xrf folder, skip those
                # convert the elements to a dataframe, with x and y and the element names as the columns
                for k, v in element.items():
                    # convert the wide format to long format
                    v = v.reset_index()
                    v = pd.melt(v,id_vars=['index'], var_name='y', value_name=k)
                    v = v.rename(columns={'index': 'x'})
                    element[k] = v
                # concatenate all the elements to a single dataframe, with x,y as the common keys
                self.elements[a_folder] = pd.concat(list(element.values()), axis=1).loc[:,~pd.concat(list(element.values()), axis=1).columns.duplicated()]

    def mask_xrf_data(self,by='Fe'):
        """mask the xrf data by the element Fe"""
        if self.elements is None:
            self.read_all_elements()
        # mask the xrf data by the element Fe
        # do a k means clustering on the Fe data
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=2)
        for a_folder in self.elements.keys():
            kmeans.fit(self.elements[a_folder][by].values.reshape(-1, 1))
            # get the cluster centers
            cluster_centers = kmeans.cluster_centers_
            # get the cluster labels
            cluster_labels = kmeans.labels_
            # get the cluster with the higher mean
            cluster = np.argmax(cluster_centers)

            # mask the xrf data by the cluster
            self.elements[a_folder]['mask'] = cluster_labels == cluster
            # save the mask as a image in the folder,use a discrete colormap
            plt.imshow(self.elements[a_folder].pivot(
                index='x', columns='y', values='mask'
            ), cmap='viridis')
            plt.axis('off')
            plt.savefig(os.path.join(self.xrf_folder, a_folder, 'mask.png'))
            plt.close()

    def transform_xrf_data(self):
        for a_folder in self.elements.keys():
            # loop through the solver_xray keys
            for k, v in self.app.solvers_depth.items():
                # test if the key image is in the folder
                if k in [i.replace(' ','_') for i in os.listdir(os.path.join(self.xrf_folder,a_folder))]:
                    self.elements[a_folder]['d'] = v.transform(self.elements[a_folder][['y', 'x']].values)[:,0]
            # save the transformed data to the folder
            self.elements[a_folder].to_csv(os.path.join(self.xrf_folder, a_folder, 'transformed.csv'), index=False)

    def prepare_for_xrf(self):
        """prepare the app for XRF data"""
        # ask the user for the by element
        by = simpledialog.askstring("Input", "Enter the element to mask the XRF data by", initialvalue='Video')
        by = by.strip()
        # add the xrf data to the app
        self.read_all_elements()
        # mask the xrf data by the element Fe
        # pop up a window to ask for the element to mask the xrf data

        self.mask_xrf_data(by=by)
        # transform the xrf data to the real world
        self.transform_xrf_data()


def main():
    app = MainApplication()
    app.main()


if __name__ == "__main__":
    main()
