import logging
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk, messagebox
import os
from msiAlign.downcore_profile import calc_depth_profile, show_analysis_selector
from msiAlign.metadata_crawler import crawl_metadata
from msiAlign.objects import XrayImage, MsiImage


def how_to_use():
    """open a webpage to show how to use the software"""
    try:
        import webbrowser
        webbrowser.open("https://github.com/weimin-liu/msiAlign/blob/main/README.md")
    except Exception as e:
        window = tk.Toplevel()
        window.title("How to use")
        text = tk.Text(window)
        text.insert(tk.END, "Please visit https://github.com/weimin-liu/msiAlign/blob/main/README.md")


class MenuBar:

    def __init__(self, app):
        self.app = app


        # create a menubar
        self.menubar = tk.Menu(self.app)
        self.app.config(menu=self.menubar)

        # Add file menu
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Add images", command=self.add_images, accelerator="Ctrl+O")
        self.app.bind("<Control-o>", self.add_images)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save workspace", command=self.app.save, accelerator="Ctrl+S")
        self.app.bind("<Control-s>", self.app.save)
        self.file_menu.add_command(label="Save layout", command=self.app.save_layout)
        self.file_menu.add_command(label="Load workspace", command=self.app.load, accelerator="Ctrl+L")
        self.app.bind("<Control-l>", self.app.load)
        self.file_menu.add_separator()
        # Add 'Open' to the file menu

        # Add 'crawl metadata' to the file menu
        self.file_menu.add_command(label="Crawl metadata", command=crawl_metadata)
        # Add 'Add metadata' to the file menu
        self.file_menu.add_command(label="Attach database", command=self.app.add_metadata)
        # Add 'Exit' to the file menu
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")
        self.app.bind("<Control-q>", self.quit)

        # Add 'View' menu
        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View", menu=self.view_menu)
        # show all tp labels next to the teaching points
        self.view_menu.add_command(label="Show TP Labels", command=self.app.show_tp_labels)
        # hide all tp labels next to the teaching points
        self.view_menu.add_command(label="Hide TP Labels", command=self.app.hide_tp_labels)
        self.view_menu.add_separator()
        # add 'Hide Teaching Points View' to the view menu
        self.view_menu.add_command(label="Toggle TP View", command=self.tg_tp_view)
        # update the teaching points view
        self.view_menu.add_command(label="Update TP View", command=self.update_tp_view)


        # Add 'Calc' menu
        self.calc_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Calc", menu=self.calc_menu)
        # Add 'Cm/Px' to the calc menu
        self.calc_menu.add_command(label="cm/px", command=self.calc_cm_per_px)
        self.calc_menu.add_separator()
        # calculate the MSI machine coordinate
        # calculate the transformation matrix
        # self.calc_menu.add_command(label="Transformation Matrix", command=self.app.calc_transformation_matrix)
        # convert the machine coordinate to real world coordinate
        self.calc_menu.add_command(label="Prep MSI", command=self.app.click_machine_to_real_world)

        self.calc_menu.add_command(label="Prep XRF", command=lambda: self.pair_tps(xrf=True))

        self.calc_menu.add_separator()
        self.calc_menu.add_command(label="Downcore Profile", command=show_analysis_selector)

        # Add a 'Dev' menu
        self.dev_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Dev", menu=self.dev_menu)
        self.menubar.entryconfig("Dev", state="disabled")
        # bind Ctrl+p to enable the dev menu
        self.app.bind("<Control-p>", self.enable_dev_menu)

        # Add labels for all the teaching points
        self.dev_menu.add_command(label="Auto add TP Labels", command=self.add_tp_labels)

        self.dev_menu.add_command(label="Pair TPs", command=self.pair_tps)
        # Add 'Reset tp' to the dev menu
        self.dev_menu.add_command(label="Reset TP", command=self.app.reset_tp)
        self.dev_menu.add_command(label="Set TP Size", command=self.app.set_tp_size)
        # move all teaching points to the top of the canvas
        self.dev_menu.add_command(label="Move All TPs to Top", command=self.app.move_all_tps_to_top)
        self.dev_menu.add_command(label="Export TPs", command=self.export_tps)
        # calculate the depth for all teaching points
        self.dev_menu.add_command(label="Calc Depth for All TPs", command=self.app.calc_depth_for_all_tps)
        self.dev_menu.add_separator()
        # lock all the images
        self.dev_menu.add_command(label="Lock All Images", command=self.app.lock_all)
        self.dev_menu.add_separator()
        self.dev_menu.add_command(label="MSI Machine Coord", command=self.app.calc_msi_machine_coordinate)
        self.dev_menu.add_separator()
        # a simple way to view the BLOB data in the database
        self.dev_menu.add_command(label="View BLOB Data", command=self.app.view_blob_data)


        # Add 'Help' menu
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        # Add 'About' to the help menu
        self.help_menu.add_command(label="How to use", command=how_to_use)
        # Add an 'Issue' to the help menu
        self.help_menu.add_command(label="Report an issue", command=report_issue)


    def enable_dev_menu(self, event=None):
        """Enable the dev menu"""
        self.menubar.entryconfig("Dev", state="normal")
        # add a message pop-up to show the dev menu is enabled
        messagebox.showinfo("Dev Menu", "Developer menu is enabled")
        # unbind the Ctrl+p to prevent the dev menu from being enabled again
        self.app.unbind("<Control-p>")
        return "break"

    def add_tp_labels(self):
        """Add labels for all the teaching points"""
        label_idx = 0
        for k, v in self.app.items.items():
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
        self.app.show_tp_labels()

    def add_images(self, event=None):
        """Load the images from the file paths"""
        file_paths = filedialog.askopenfilenames(title="Select image files",
                                                 filetypes=[("Image files", "*.png *.jpg *.tif")])

        for file_path in file_paths:
            for k, v in self.app.items.items():
                try:
                    if k == os.path.basename(file_path):
                        messagebox.showerror("Error", f"{file_path} has already been loaded")
                        return
                except AttributeError:
                    pass
            # let the user choose if input image is a reference image or a MSI image
            image_type = messagebox.askyesnocancel(
                "Image Type", "Is this a reference image (e.g., xray, linescan...) or not (e.g., MSI, xrf...)?"
            )  # if the user cancels, the image is an msi image
            if image_type:
                loaded_image = XrayImage.from_path(file_path)
            elif image_type is False:
                loaded_image = MsiImage.from_path(file_path)
            else:
                messagebox.showerror("Error", "You need to choose an image type")

            logging.debug(f"Loaded image: {loaded_image}")
            loaded_image.create_im_on_canvas(self.app)
            self.app.items[loaded_image.tag] = loaded_image

    def quit(self, event=None):
        self.app.quit()

    def generate_tree_view(self):
        """generate a tree view using the teaching points, with the parent node being the image tag"""
        # clear the tree view
        self.app.tree.delete(*self.app.tree.get_children())
        # get the teaching points
        for k, v in self.app.items.items():
            try:
                if v.teaching_points is not None:
                    # add the image tag to the tree view
                    parent = self.app.tree.insert("", "end", text=k, values=("image", "", "", ""))
                    # add the teaching points to the tree view
                    for i, tp in v.teaching_points.items():
                        self.app.tree.insert(parent, "end", text=i, values=("", tp[0], tp[1], tp[2]))
            except AttributeError:
                pass

    def update_tp_view(self):
        # if the teaching points view does not exist, create one
        if not hasattr(self.app, 'tree'):
            logging.debug("Creating a treeview to display teaching points")
            # create a treeview to display teaching points
            self.app.tree_frame = tk.Frame(self.app)
            self.app.tree_frame.pack(side=tk.RIGHT, fill=tk.Y)
            self.app.tree = ttk.Treeview(self.app.tree_frame,
                                         columns=('label', 'x', 'y', 'd'),
                                         selectmode='browse')
            self.app.tree.heading('#0', text='img')
            self.app.tree.heading('label', text='label')
            self.app.tree.heading('x', text='x')
            self.app.tree.heading('y', text='y')
            self.app.tree.heading('d', text='d')
            self.app.tree.column('#0', width=100)
            self.app.tree.column('label', width=50)
            self.app.tree.column('x', width=50)
            self.app.tree.column('y', width=50)
            self.app.tree.column('d', width=50)
            self.app.tree.pack(side=tk.LEFT, fill=tk.Y)
            self.app.tree_visible = True
        # update the teaching points view
        self.generate_tree_view()

    def tg_tp_view(self):
        """Toggle the visibility of the teaching points view"""
        if self.app.tree_visible:
            self.app.tree_frame.pack_forget()
            self.app.tree_visible = False
        else:
            self.app.tree_frame.pack(side=tk.RIGHT, fill=tk.Y)
            self.app.tree_visible = True

    def calc_cm_per_px(self):
        # get the two vertical scale lines
        if len(self.app.scale_line) < 2:
            messagebox.showerror("Error", "You need to draw two vertical lines to calculate the scale")
            raise ValueError("You need to draw two vertical lines to calculate the scale")
        elif len(self.app.scale_line) > 2:
            messagebox.showerror("Error", f"You have drawn more than two vertical lines:{self.app.scale_line} ")
            raise ValueError("You have drawn more than two vertical lines")
        else:
            # calculate the distance between the two scale lines
            pixel_distance = abs(
                self.app.canvas.coords(self.app.scale_line[1])[0] - self.app.canvas.coords(self.app.scale_line[0])[0])
            # calculate the distance in real world
            real_distance = simpledialog.askfloat("Real Distance", "Real Distance (cm):")
            # calculate the scale
            self.app.cm_per_pixel = real_distance / pixel_distance
            # create a text on the canvas to display the scale
            text = tk.Text(self.app.canvas, height=1, width=20)
            text.insert(tk.END, f"1cm = {int(1 / self.app.cm_per_pixel)} pixel")
            text.config(state="disabled")
            self.app.canvas.create_window(100, 100, window=text, tags="cm_per_px_text")

    def export_tps(self):
        """Export the teaching points to a json file"""
        file_path = filedialog.asksaveasfilename(title="Export Teaching Points", filetypes=[("JSON files", "*.json")])
        if file_path:
            self.app.export_tps(file_path)
            messagebox.showinfo("Export Teaching Points", f"Teaching points have been exported to {file_path}")
        else:
            messagebox.showinfo("Export Teaching Points", "No file path is given")

    def pair_tps(self, auto=False,xrf=False):
        """pair the teaching points from xray images and msi images"""
        # create a pop-up text window to input the pair of teaching points
        popup = tk.Toplevel()
        popup.title("Pair Teaching Points")
        popup.geometry("300x200")
        # create a text input box to input the pair of teaching points that are strecthable by the user
        text = tk.Text(popup, height=10, width=30)
        text.grid(row=0, column=0, sticky="nsew")
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(0, weight=1)
        auto_label_button = tk.Button(popup, text="I forgot to label, label them all now",
                                      command=lambda: self.add_tp_labels())
        auto_label_button.grid(row=1, column=0, sticky="nsew")

        # create a button to submit the pair of teaching points
        submit_button = tk.Button(popup, text="Submit",
                                  command=lambda: self.app.pair_tps(text.get("1.0", "end-1c"),
                                                                    auto=auto,
                                                                    xrf=xrf))
        submit_button.grid(row=2, column=0, sticky="nsew")
        # create a button to fill in the pair of teaching points
        fill_button = tk.Button(popup, text="Fill", command=lambda: text.insert(tk.END, self.app.fill_tps_str()))
        fill_button.grid(row=3, column=0, sticky="nsew")




def report_issue():
    try:
        import webbrowser
        webbrowser.open("https://github.com/weimin-liu/msiAlign/issues")
    except Exception as e:
        messagebox.showinfo("Report an issue",
                            "Please report the issue at https://github.com/weimin-liu/msiAlign/issues")

