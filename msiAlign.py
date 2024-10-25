import json
import logging
import os
import re
import sqlite3
import sys
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk, simpledialog, messagebox
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import tqdm

from msiAlign.func import CorSolver, sort_points_clockwise, sort_points_clockwise_by_keys
from msiAlign.menubar import MenuBar
from msiAlign.objects import LoadedImage, VerticalLine, MsiImage, XrayImage, TeachableImage
from msiAlign.rclick import RightClickOnLine, RightClickOnImage, RightClickOnTeachingPoint


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        # create a logger, and save the log to a file
        logging.basicConfig(filename="msiAlign.log", level=logging.DEBUG,
                            format="%(asctime)s:%(levelname)s:%(message)s",
                            filemode='a')

        self.geometry("1200x800")
        self.canvas = None
        self.right_click_on_tp = None
        self.right_click_on_image = None
        self.right_click_on_line = None
        self.title('msiAlign')
        self.items = {}
        self.create_canvas()
        self.xrf_folder = None


        self.database_path = None

        self.scale_line = []
        self.sediment_start = None

        self.cm_per_pixel = None
        # add menubar
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
            logging.debug(f"event.delta: {event.delta}")
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
            logging.debug(f"event.delta: {event.delta}")
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

    def view_blob_data(self):
        # get a popup window to choose SPEC_ID and COLUMN_NAME
        popup = tk.Toplevel()
        popup.title("View BLOB Data")
        popup.geometry("300x200")
        # create a label to display the SPEC_ID
        spec_id_label = tk.Label(popup, text="SPEC_ID:")
        spec_id_label.pack()
        spec_id_entry = tk.Entry(popup)
        spec_id_entry.pack()
        # create a label to display the COLUMN_NAME
        column_name_label = tk.Label(popup, text="COLUMN_NAME:")
        column_name_label.pack()
        column_name_entry = tk.Entry(popup)
        column_name_entry.pack()
        # create a label to display the Table Name
        table_name_label = tk.Label(popup, text="Table Name:")
        table_name_label.pack()
        table_name_entry = tk.Entry(popup)
        table_name_entry.pack()
        # create a button to submit the SPEC_ID and COLUMN_NAME
        submit_button = tk.Button(popup, text="Submit", command=lambda: self.get_blob_data(spec_id_entry.get(),
                                                                                           table_name_entry.get(),
                                                                                           column_name_entry.get()))
        submit_button.pack()

    def flip_image(self, item):
        """ flip the image upside down, call the flip method of the LoadedImage object"""
        self.items[item].flip()
        self.canvas.itemconfig(item, image=self.items[item].tk_img)

    def get_blob_data(self, spec_id, table_name, column_name):
        if self.database_path is None:
            file_path = filedialog.askopenfilename(title="Select a database file", filetypes=[("SQLite files", "*.db")])
            if file_path:
                database_path = file_path
            else:
                raise ValueError("You need to select a database file")
        else:
            database_path = self.database_path
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT {column_name} FROM {table_name} WHERE spec_id={spec_id};")
        blob = cursor.fetchone()[0]
        conn.close()

        if 'spot' in column_name:
            array = np.frombuffer(blob, dtype=np.int64).reshape(-1, 2)
        else:
            array = np.frombuffer(blob, dtype=np.float64).reshape(-1, 2)
        logging.debug(f"array: {array}")

        # popup a window to display the blob data and add a scrollbar
        popup = tk.Toplevel()
        popup.title("BLOB Data")
        popup.geometry("800x600")
        container = tk.Frame(popup)
        container.pack(fill=tk.BOTH, expand=True)
        # create a treeview to display the blob data
        tree = ttk.Treeview(container, show="headings")
        # Initialize Treeview columns on first load
        tree['columns'] = ['x', 'y']
        tree.heading('x', text='x')
        tree.heading('y', text='y')
        # add a scrollbar to the treeview
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        # Pack the Treeview and Scrollbar in the container frame
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill="y")
        # insert the blob data to the treeview
        for i, row in enumerate(array):
            tree.insert("", "end", values=(row[0], row[1]))
        conn.close()

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
        # update the canvas item with the new image
        logging.debug(f"item: {item}, image: {self.items[item].tk_img}")
        logging.debug(f"self.items[item]: {self.items[item]}")
        logging.debug('Image resized')
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
                logging.debug(f"v.tag: {v.tag}")
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
            logging.debug(f'the front image is {clicked_images[-1]}')
            return clicked_images[-1]
        else:
            return None

    def lock_all(self):
        # invoke lock_image method for all the images
        for k, v in self.items.items():
            if isinstance(v, LoadedImage):
                self.right_click_on_image.lock_image(k)
        messagebox.showinfo("Done", "All the images are locked")

    def move_all_tps_to_top(self):
        # move all the teaching points (with tag 'tp_*') in canvas to the top
        tps = self.find_wildcard('tp_')
        for tp in tps:
            self.canvas.tag_raise(tp)
        messagebox.showinfo("Done", "All the teaching points are moved to the top")

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

    def show_tp_labels(self):
        """ display the labels of the teaching points on the canvas"""
        for k, v in self.items.items():
            if isinstance(v, TeachableImage):
                v.show_tp_labels(self)

    def hide_tp_labels(self):
        """delete all the text items on the canvas labeled 'tp_labels'"""
        self.canvas.delete('tp_labels')


    def calc_transformation_matrix(self, auto=False):
        """ solve the transformation among MSi coordinates, xray pixel coordinates, and line scan depth"""
        # get all fixed points from xray teaching points
        xray_tps = []
        linescan_tps = []
        for k, v in self.items.items():
            if isinstance(v, XrayImage):
                logging.debug(f"v.tag: {v.tag} \n v.teaching_points: {v.teaching_points}")
                xray_tps.extend(v.teaching_points.values())
        # get all fixed points from xray teaching points
        xray_ds = []
        for i, v in enumerate(xray_tps):
            xray_ds.append(v[2])
            linescan_tps.append([v[2], v[1]])
            xray_tps[i] = v[:2]

        # sort the xray_tps by the x coordinate, and cut them to groups, each with 3 points
        xray_tps = sorted(xray_tps, key=lambda x: x[0])
        xray_tps = [xray_tps[i:i + 3] for i in range(0, len(xray_tps), 3)]
        # sort the xray_ds, and cut them to groups, each with 3 points, and get the average depth
        xray_ds = sorted(xray_ds)
        xray_ds = [xray_ds[i:i + 3] for i in range(0, len(xray_ds), 3)]
        xray_ds = [np.mean(d) for d in xray_ds]

        logging.debug(f"xray_tps: {xray_tps}")
        # in each group, sort the points clockwise
        for i, group in enumerate(xray_tps):
            xray_tps[i] = sort_points_clockwise(np.array(group))
            logging.debug(f"group: {group}")

        # sort the linescan_tps by the x coordinate, and cut them to groups, each with 3 points
        linescan_tps = sorted(linescan_tps, key=lambda x: x[0])
        linescan_tps = [linescan_tps[i:i + 3] for i in range(0, len(linescan_tps), 3)]
        # in each group, sort the points clockwise
        for i, group in enumerate(linescan_tps):
            linescan_tps[i] = sort_points_clockwise(np.array(group))
            logging.debug(f"group: {group}")

        msi_tps = {}
        msi_ds = {}

        for k, v in self.items.items():
            if isinstance(v, MsiImage):
                msi_tps[k] = v.teaching_points
        for k, v in msi_tps.items():
            logging.debug(f"{np.array(list(v.values()))}")
            msi_ds[k] = np.array(list(v.values()))[:, 2].mean()
            msi_tps[k] = np.array(list(v.values()))[:, :2]
            # sort msi_tps  clockwise by the keys of msi_tps
            msi_tps[k] = sort_points_clockwise_by_keys(np.array(msi_tps[k]), np.array(list(v.keys())))

        # solve the affine transformation of how to transform from msi_tps to xray_tps
        self.solvers_xray = {}
        self.solvers_depth = {}
        for k, v in msi_tps.items():
            msi_d = msi_ds[k]
            # find the index of the xray teaching points that are closest to the msi teaching points
            diff = np.abs(np.array(xray_ds) - msi_d)
            idx = np.argmin(diff)

            assert diff.min() < 0.5, f"vertical_distance: {diff.min()} is too large"

            # get the xray teaching points that are closest to the msi teaching points
            self.solvers_xray[k] = CorSolver()
            self.solvers_xray[k].fit(v, xray_tps[idx])
            # solve the transformation of how to transform from msi_tps to line_scan_tps
            self.solvers_depth[k] = CorSolver()
            self.solvers_depth[k].fit(v, linescan_tps[idx])
        # create a popup window to show the process is done, and ok button to close the window
        messagebox.showinfo("Done", "The transformation matrix was calculated.")

        if auto:
            self.machine_to_real_world()

    def fill_tps_str(self):
        try:
            return self.pair_tp_str
        except AttributeError:
            return ""

    def pair_tps(self, str1, auto=False,xrf=False):
        logging.debug(f"input: {str1}")
        self.pair_tp_str = str1
        # remove the leading and trailing white spaces
        str1 = str1.strip()
        # convert the input string to a list of tuples
        str1 = str1.split('\n')
        str1 = [s.split(' ') for s in str1]

        str1 = [[int(x) for x in s] for s in str1]
        logging.debug(f"str1: {str1}")
        paired_tps = str1
        logging.debug(f"paired_tps: {paired_tps}")
        # get all teaching points from xray:
        for k, v in self.items.items():
            if isinstance(v, XrayImage):
                xray_tps = v.label_indexed_teaching_points
                break
        # get all their labels
        xray_tp_labels = list(xray_tps.keys())
        logging.debug(f"xray_tp_labels: {xray_tp_labels}")
        # convert self.paired_tps to a dictionary using xray_tp_labels as the values
        paired_tps_dict = {}
        for i, v in enumerate(paired_tps):
            if v[0] in xray_tp_labels:
                paired_tps_dict[v[1]] = v[0]
            elif v[1] in xray_tp_labels:
                paired_tps_dict[v[0]] = v[1]
            else:
                logging.debug(f"v: {v} is not in xray_tp_labels")
        logging.debug(f"paired_tps_dict: {paired_tps_dict}")

        self.solvers_xray = {}
        self.solvers_depth = {}

        logging.debug(f"xray_tps: {xray_tps}")
        for k, v in self.items.items():
            if isinstance(v, MsiImage):
                try:
                    msi_tps = v.label_indexed_teaching_points
                    # find the teaching points that have the paired label in xray_tps
                    partial_xray_tps = {}
                    for msi_tp_label in msi_tps.keys():
                        if msi_tp_label in paired_tps_dict.keys():
                            partial_xray_tps[msi_tp_label] = xray_tps[paired_tps_dict[msi_tp_label]]
                    logging.debug(f"partial_xray_tps: {partial_xray_tps}")
                    self.solvers_xray[k] = CorSolver()
                    self.solvers_xray[k].fit(np.array(list(msi_tps.values()))[:, 0:2],
                                             np.array(list(partial_xray_tps.values()))[:, 0:2])
                    self.solvers_depth[k] = CorSolver()
                    self.solvers_depth[k].fit(np.array(list(msi_tps.values()))[:, 0:2],
                                              np.array(list(partial_xray_tps.values()))[:, [2, 1]])
                except Exception as e:
                    messagebox.showerror("Error", f"Error: {e}")
        # create a popup window to show the process is done, and ok button to close the window
        messagebox.showinfo("Done", "The teaching points are paired and the transformation matrix was calculated.")

        if auto:
            self.machine_to_real_world()

        if xrf:
            self.prepare_for_xrf()

    def calc_msi_machine_coordinate(self):
        for k, v in self.items.items():
            if isinstance(v, MsiImage):
                logging.debug(f"Calculating the MSI machine coordinate for {k}")
                try:
                    v.update_tp_coords(self.database_path)
                except AttributeError:
                    logging.debug(f"database path is not set")

    def click_machine_to_real_world(self):
        # test if metadata is added
        if self.database_path is None:
            # create a messagebox to show that the metadata is not added yet
            userchoice = messagebox.askokcancel(
                "Metadata is not added yet",
                "Do you want to add metadata now?",
                icon='warning'
            )
            if userchoice:
                self.add_metadata()
            else:
                return

        # calculate the MSI machine coordinate

        self.calc_msi_machine_coordinate()
        # create a messagebox to ask if the user wants to pair the teaching points automatically or manually

        user_choice = messagebox.askquestion("Pair Teaching Points",
                                             "Do you want to pair the teaching points automatically (yes) or manually (no)?",
                                             icon='warning')
        if user_choice == 'yes':
            self.calc_transformation_matrix(auto=True)
        else:
            self.menu.pair_tps(auto=True)

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
                )) if f.endswith('.txt') and 'Video' not in f]
                logging.debug(f"xrf_files: {xrf_files}")
                element = {}
                # read all the elements from the xrf images
                # find the changing parts and the common parts of all names
                common_part = os.path.commonprefix(xrf_files)
                logging.debug(f"common_part: {common_part}")
                changing_parts = [f.replace(common_part, '').replace('.txt', '') for f in xrf_files]
                logging.debug(f"changing_parts: {changing_parts}")
                for i, f in enumerate(xrf_files):
                    element[changing_parts[i]] = pd.read_csv(os.path.join(self.xrf_folder,a_folder, f), sep=';',header=None)
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
            # drop the 0 mask
            self.elements[a_folder] = self.elements[a_folder][self.elements[a_folder]['mask']]

    def transform_xrf_data(self):
        for a_folder in self.elements.keys():
            # loop through the solver_xray keys
            for k, v in self.solvers_depth.items():
                # test if the key image is in the folder
                if k in [i.replace(' ','_') for i in os.listdir(os.path.join(self.xrf_folder,a_folder))]:
                    self.elements[a_folder]['d'] = v.transform(self.elements[a_folder][['y', 'x']].values)[:,0]
            # save the transformed data to the folder
            self.elements[a_folder].to_csv(os.path.join(self.xrf_folder, a_folder, 'transformed.csv'), index=False)

    def prepare_for_xrf(self):
        """prepare the app for XRF data"""
        # add the xrf data to the app
        self.read_all_elements()
        # mask the xrf data by the element Fe
        self.mask_xrf_data()
        # transform the xrf data to the real world
        self.transform_xrf_data()

    def machine_to_real_world(self):
        """apply the transformation to the msi teaching points"""
        # ask for the sqlite file to read the metadata
        if self.database_path is None:
            file_path = filedialog.askopenfilename(title="Select a database file", filetypes=[("SQLite files", "*.db")])
            if file_path:
                self.database_path = file_path
            else:
                messagebox.showerror("No file path is given")
        # connect to the sqlite database
        file_path = self.database_path
        if file_path:
            # connect to the sqlite database
            conn = sqlite3.connect(file_path)
            c = conn.cursor()
            try:
                # check if the transformation table exists
                c.execute('SELECT * FROM transformation')
            except sqlite3.OperationalError:
                logging.debug("The transformation table does not exist yet, creating one")
                # create a transformation table with metadata(spec_id) as the reference key
                c.execute(
                    'CREATE TABLE transformation (spec_id INTEGER, msi_img_file_name TEXT, spot_array BLOB, xray_array BLOB, linescan_array BLOB, FOREIGN KEY(spec_id) REFERENCES metadata(spec_id))')
                conn.commit()
                # read all the spotname from metadata table and convert them to array
                c.execute('SELECT spec_id, msi_img_file_name, spot_name FROM metadata')
                data = c.fetchall()
                assert len(data) > 0, "No data is found in the metadata table"
                for row in tqdm.tqdm(data):
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
                    # store_blob_info(conn, 'spot_array', spot_name.dtype, spot_name.shape)

            c.execute('SELECT spec_id, msi_img_file_name, spot_array FROM transformation')
            data = c.fetchall()
            for row in data:
                spec_id, im_name, spot_array = row
                spec_id = int(spec_id)
                spot_array = np.frombuffer(spot_array, dtype=int).reshape(-1, 2)
                logging.debug(f"spec_id: {spec_id}, im_name: {im_name}, spot_array: {spot_array}")
                # apply the transformation to the spot_array
                if im_name in self.solvers_xray.keys():
                    xray_array = self.solvers_xray[im_name].transform(spot_array)
                    xray_array_dtype = xray_array.dtype
                    logging.debug(f"xray_array_dtype: {xray_array_dtype}")
                    # store_blob_info(conn, 'xray_array', xray_array_dtype, xray_array.shape)
                    xray_array_shape = xray_array.shape
                    logging.debug(f"xray_array_shape: {xray_array_shape}")
                    linescan_array = self.solvers_depth[im_name].transform(spot_array)
                    # line_scan_dtype = linescan_array.dtype
                    # linescan_array_shape = linescan_array.shape
                    # store_blob_info(conn, 'linescan_array', line_scan_dtype, linescan_array_shape)
                    c.execute('UPDATE transformation SET xray_array = ? WHERE spec_id = ?',
                              (xray_array.tobytes(), spec_id))
                    c.execute('UPDATE transformation SET linescan_array = ? WHERE spec_id = ?',
                              (linescan_array.tobytes(), spec_id))
                else:
                    logging.debug(f"{im_name} is not in the solvers_xray.keys()")
            # store the blob info to the blob_info table

            conn.commit()

            conn.close()
        else:
            messagebox.showerror("No file path is given")

        # create a popup window to show the process is done, and ok button to close the window
        messagebox.showinfo("Done", "The transformation is applied to the MSI coords")

    def set_tp_size(self):
        """set the size of the teaching points"""
        size = simpledialog.askinteger("Input", "Enter the size of the teaching points", initialvalue=5)
        size = size if size is not None else 5
        for k, v in self.items.items():
            if isinstance(v, TeachableImage):
                v.tp_size = size

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
        if not isinstance(clicked_image, XrayImage) and not isinstance(clicked_image, MsiImage):
            messagebox.showerror("Wrong image", "Click an xray image or a MSI image to add a teaching point")
            return
        if clicked_image is not None:
            clicked_image.add_teaching_point(event, self)

    def add_metadata(self):
        """Add metadata to the app"""
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
        for row in data:
            im_name, px_rect, msi_rect = row
            im_name = im_name
            # attach the metadata to the corresponding image
            try:
                self.items[im_name].px_rect = eval(px_rect)
                self.items[im_name].msi_rect = eval(msi_rect)
                logging.debug(f"px_rect: {self.items[im_name].px_rect}, msi_rect: {self.items[im_name].msi_rect}")
            except KeyError:
                pass
        conn.close()
        # create a popup window to show the process is done, and ok button to close the window
        messagebox.showinfo("Done", "The metadata is added")

    def use_as_ref_to_resize(self, item):
        """use the selected image as the reference to resize other images"""
        ref_width = self.items[item].thumbnail.width
        for k, v in self.items.items():
            logging.debug(f"{k} has the class of {v.__class__}")
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

    def reset(self, no_warning=False):
        if not no_warning:
            userchoice=tk.messagebox.showwarning("Warning", "This will reset the canvas, are you sure?")
        else:
            userchoice = 'yes'
        if userchoice == 'yes':
            # reset the canvas
            self.canvas.delete("all")
            self.items = {}
            self.cm_per_pixel = None
            self.database_path = None
            self.pair_tp_str = None
            self.scale_line = []
            self.sediment_start = None
            self.pair_tp_str = None
            self.solvers_xray = {}
            self.solvers_depth = {}
        else:
            pass

    def save(self, event=None, layout_only=False):
        """Save the current state of the canvas"""
        # get the file path to save the state
        file_path = filedialog.asksaveasfilename(title="Save workspace", filetypes=[("JSON", "*.json")])
        data_to_save = {"cm_per_pixel": self.cm_per_pixel, "items": [], 'database_path': self.database_path,}

        try:
            data_to_save["pair_tp_str"] = self.pair_tp_str
        except AttributeError:
            pass

        try:
            data_to_save["scale_line0"] = self.scale_line[0]
            data_to_save["scale_line1"] = self.scale_line[1]
        except IndexError:
            pass
        data_to_save["sediment_start"] = self.sediment_start

        # save the treeview in json format
        for k, v in self.items.items():
            if not layout_only:
                data_to_save["items"].append(v.to_json())
            else:
                # save the images excluding the msi images
                if not isinstance(v, MsiImage):
                    data_to_save["items"].append(v.to_json())
        with open(file_path, "w") as f:
            json.dump(data_to_save, f)

    def load(self, event=None):
        """Load the state of the canvas"""
        file_path = filedialog.askopenfilename(title="Select a workspace file", filetypes=[("JSON files", "*.json")])
        with open(file_path, "r") as f:
            data = json.load(f)
            # reset the canvas
            self.reset(no_warning=True)
            try:
                self.cm_per_pixel = data["cm_per_pixel"]
                if self.cm_per_pixel is not None:
                    # print the cm_per_pixel on canvas
                    # create a text on the canvas to display the scale
                    text = tk.Text(self.canvas, height=1, width=20)
                    text.insert(tk.END, f"1cm = {int(1 / self.cm_per_pixel)} pixel")
                    text.config(state="disabled")
                    self.canvas.create_window(100, 100, window=text, tags="cm_per_px_text")
            except KeyError:
                logging.debug("No cm_per_pixel is found")
                pass
            try:
                self.database_path = data["database_path"]
            except KeyError:
                pass
            try:
                self.pair_tp_str = data["pair_tp_str"]
            except KeyError:
                pass

            for item in data["items"]:
                if "MsiImage" in item["type"]:
                    loaded_image = MsiImage.from_json(item, self)
                    self.items[loaded_image.tag] = loaded_image
                elif "XrayImage" in item["type"]:
                    loaded_image = XrayImage.from_json(item, self)
                    self.items[loaded_image.tag] = loaded_image
                elif item["type"] == "VerticalLine":
                    vertical_line = VerticalLine.from_json(item, self)
                    self.items[vertical_line.tag] = vertical_line
                    self.bind_events_to_vertical_lines(vertical_line)
            try:
                self.scale_line.append(data["scale_line0"])
                self.scale_line.append(data["scale_line1"])
                # set the scale line to green
                self.canvas.itemconfig(self.scale_line[0], fill="blue")
                self.canvas.itemconfig(self.scale_line[1], fill="blue")
            except KeyError:
                logging.debug("No scale line is found")
                pass
            try:
                self.sediment_start = data["sediment_start"]
                self.canvas.itemconfig(self.sediment_start, fill="green")
            except KeyError:
                logging.debug("No sediment start is found")
                pass

    def export_tps(self, file_path):
        """Export the teaching points to a json file"""
        data_to_save = "img;x;y;d\n"
        for k, v in self.items.items():
            if hasattr(v, "teaching_points"):
                for k, tp in v.teaching_points.items():
                    data_to_save += f"{v.tag};{tp[0]};{tp[1]};{tp[2]}\n"
        with open(file_path, "w") as f:
            f.write(data_to_save)

    def find_wildcard(self, wildcard):
        """find the tag with the wildcard"""
        items = self.canvas.find_all()
        matched_items = []
        for item in items:
            logging.debug(f"item: {item}, tags: {self.canvas.gettags(item)[0]}")
            if wildcard in self.canvas.gettags(item)[0]:
                matched_items.append(self.canvas.gettags(item))
        return matched_items

    def calc_depth_for_all_tps(self):
        """calculate the depth for all the teaching points"""
        if self.sediment_start is None:
            messagebox.showerror("Error", "No sediment start is found")
            return
        if self.cm_per_pixel is None:
            messagebox.showerror("Error", "No cm_per_pixel is found")
            return
        user_choice1 = messagebox.askyesno("Warning",
                                           "This will overwrite the current depth of the teaching points,"
                                           " are you sure?")
        user_choice2 = messagebox.askyesno("Warning",
                                           "If you have moved the xray images after setting the teaching points, "
                                           "the depth will be incorrect, are you sure?")

        if user_choice1 and user_choice2:
            for k, v in self.items.items():
                if isinstance(v, TeachableImage):
                    try:
                        for px_coords, values in v.teaching_points.items():
                            depth = abs(self.canvas.coords(self.sediment_start)[0] - px_coords[0]) * self.cm_per_pixel
                            _tmp = list(values)
                            _tmp[2] = depth
                            v.teaching_points[px_coords] = tuple(_tmp)
                    except Exception as e:
                        messagebox.showerror("Error", f"Error: {e}")
                    try:
                        for px_coords, values in v.teaching_points_px_coords.items():
                            depth = abs(self.canvas.coords(self.sediment_start)[0] - px_coords[0]) * self.cm_per_pixel
                            _tmp = list(values)
                            _tmp[2] = depth
                            v.teaching_points_px_coords[px_coords] = tuple(_tmp)
                    except AttributeError:
                        pass

            messagebox.showinfo("Done", "The depth for all the teaching points are calculated")

    def reset_tp(self):
        """
        Reset the teaching points
        """
        # remove all the teaching points from the canvas
        logging.debug("Resetting teaching points")
        for k, v in self.items.items():
            if isinstance(v, TeachableImage):
                if v.teaching_points is not None:
                    v.teaching_points = {}
                    logging.debug(f"Reset teaching points attributes for {k} successfully")
                if hasattr(v, "teaching_points_updated"):
                    v.teaching_points_updated = False
                    logging.debug(f"Reset teaching_points_updated attributes for {k} successfully")
        # hard remove all the teaching points oval from the canvas with tag including 'tp_'
        try:
            # list all tags
            tps = self.find_wildcard('tp_')
            logging.debug(f"tps: {tps}")
            for tp in tps:
                try:
                    self.canvas.delete(tp[0])
                except IndexError:
                    self.canvas.delete(tp)
        except AttributeError:
            pass
        messagebox.showinfo("Done", "All the teaching points are removed")

        # clear the tree view
        try:
            self.tree.delete(*self.tree.get_children())
            logging.debug("Reset the tree view successfully")
        except AttributeError:
            logging.debug("No tree view found")
            pass

    def main(self):
        self.mainloop()


def main():
    app = MainApplication()
    app.main()


if __name__ == "__main__":
    main()
