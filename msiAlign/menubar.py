import tkinter as tk
from tkinter import filedialog, simpledialog, ttk
import logging

from msiAlign.metadata_crawler import crawl_metadata
from msiAlign.objects import XrayImage, LinescanImage, MsiImage
from scripts.to1d import get_depth_profile_from_gui


class MenuBar:

    def __init__(self, app):
        self.app = app

        # create a menubar
        self.menubar = tk.Menu(self.app)
        self.app.config(menu=self.menubar)

        # Add file menu
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Add images", command=self.add_images)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save workspace", command=self.app.save)
        self.file_menu.add_command(label="Load workspace", command=self.app.load)
        self.file_menu.add_separator()
        # Add 'Open' to the file menu

        # Add 'crawl metadata' to the file menu
        self.file_menu.add_command(label="Crawl metadata", command=crawl_metadata)
        # Add 'Add metadata' to the file menu
        self.file_menu.add_command(label="Attach database", command=self.app.add_metadata)
        # Add 'Exit' to the file menu
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.quit)

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
        self.view_menu.add_separator()
        # a simple way to view the BLOB data in the database
        self.view_menu.add_command(label="View BLOB Data", command=self.app.view_blob_data)

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
        self.calc_menu.add_command(label="Machine to Real World", command=self.app.click_machine_to_real_world)
        self.calc_menu.add_separator()
        self.calc_menu.add_command(label="Downcore Profile", command=calc_depth_profile)

        # Add a 'Dev' menu
        self.dev_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Dev", menu=self.dev_menu)
        # Add labels for all the teaching points
        self.dev_menu.add_command(label="Auto add TP Labels", command=self.add_tp_labels)

        self.dev_menu.add_command(label="Pair TPs", command=self.pair_tps)
        # Add 'Reset tp' to the dev menu
        self.dev_menu.add_command(label="Reset TP", command=self.app.reset_tp)
        self.dev_menu.add_command(label="Set TP Size", command=self.app.set_tp_size)
        # move all teaching points to the top of the canvas
        self.dev_menu.add_command(label="Move All TPs to Top", command=self.app.move_all_tps_to_top)
        self.dev_menu.add_separator()
        # lock all the images
        self.dev_menu.add_command(label="Lock All Images", command=self.app.lock_all)
        self.dev_menu.add_separator()
        self.dev_menu.add_command(label="MSI Machine Coord", command=self.app.calc_msi_machine_coordinate)


        # Add 'Export' menu
        self.export_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Export", menu=self.export_menu)
        # Add 'Export TPs' to the export menu
        self.export_menu.add_command(label="Export TPs", command=self.export_tps)

        # Add 'Help' menu
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        # Add 'About' to the help menu
        self.help_menu.add_command(label="v1.0.0", state="disabled")
        self.help_menu.add_command(label="How to use", command=self.how_to_use)
        # Add an 'Issue' to the help menu
        self.help_menu.add_command(label="Report an issue", command=report_issue)

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
                    label_idx += 1

            except AttributeError:
                pass


    def add_images(self):
        """Load the images from the file paths"""
        file_paths = filedialog.askopenfilenames()
        for file_path in file_paths:
            for k, v in self.app.items.items():
                try:
                    if v.path == file_path:
                        raise ValueError(f"{file_path} has already been loaded")
                except AttributeError:
                    pass
            if self.app.n_xray * self.app.n_linescan == 0:
                # let the user choose if input image is an xray image(x) or a linescan image(l) or an msi image (m)
                image_type = simpledialog.askstring("Image Type",
                                                    "Is this an xray image(x) or a linescan image(l) or an msi image "
                                                    "(m)?")
                if image_type == "x":
                    self.app.n_xray += 1
                    loaded_image = XrayImage.from_path(file_path)
                elif image_type == "l":
                    self.app.n_linescan += 1
                    loaded_image = LinescanImage.from_path(file_path)
                elif image_type == "m":
                    loaded_image = MsiImage.from_path(file_path)
                else:
                    raise ValueError("You need to choose an image type")
            else:
                loaded_image = MsiImage.from_path(file_path)
            logging.debug(f"Loaded image: {loaded_image}")
            loaded_image.create_im_on_canvas(self.app)
            self.app.items[loaded_image.tag] = loaded_image

    def quit(self):
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
            raise ValueError("You need to draw two vertical lines to calculate the scale")
        elif len(self.app.scale_line) > 2:
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
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if file_path:
            self.app.export_tps(file_path)
            print(f"Teaching points have been exported to {file_path}")
        else:
            print("No file path is given")

    def how_to_use(self):
        """open a webpage to show how to use the software"""
        try:
            import webbrowser
            webbrowser.open("https://github.com/weimin-liu/msiAlign/blob/main/README.md")
        except Exception as e:
            window = tk.Toplevel()
            window.title("How to use")
            text = tk.Text(window)
            text.insert(tk.END, "Please visit https://github.com/weimin-liu/msiAlign/blob/main/README.md")


    def pair_tps(self,auto=False):
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
        # create a button to submit the pair of teaching points
        submit_button = tk.Button(popup, text="Submit", command=lambda: self.app.pair_tps(text.get("1.0", "end-1c"), auto=auto))
        submit_button.grid(row=1, column=0, sticky="nsew")
        # create a button to fill in the pair of teaching points
        fill_button = tk.Button(popup, text="Fill", command=lambda: text.insert(tk.END, self.app.fill_tps_str()))
        fill_button.grid(row=2, column=0, sticky="nsew")



def report_issue():
    try:
        import webbrowser
        webbrowser.open("https://github.com/weimin-liu/msiAlign/issues")
    except Exception as e:
        window = tk.Toplevel()
        window.title("Report an issue")
        text = tk.Text(window)
        text.insert(tk.END, "Please report the issue at https://github.com/weimin-liu/msiAlign/issues")
        text.pack()
        window.mainloop()


def calc_depth_profile():
    """Calculate the depth profile"""
    # popup a window to ask for the parameters
    window = tk.Toplevel()
    # pack the window
    window.title("Calc Downcore Profile")
    # ask for the parameters
    # exported_txt_path, using file selection dialog, left is the text, right is the button for file selection
    tk.Label(window, text="Exported txt path(s):").grid(row=0, column=0, sticky='nsew')

    exported_txt_path = tk.Entry(window)
    exported_txt_path.grid(row=0, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: exported_txt_path.insert(tk.END, filedialog.askopenfilename() + ';')).grid(row=0,
                                                                                                         column=2,
                                                                                                         sticky='nsew')

    # sqlite_db_path
    tk.Label(window, text="Sqlite db path:").grid(row=1, column=0, sticky='nsew')
    sqlite_db_path = tk.Entry(window)
    sqlite_db_path.grid(row=1, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: sqlite_db_path.insert(tk.END, filedialog.askopenfilename())).grid(row=1, column=2,
                                                                                                sticky='nsew')

    # target_cmpds, able to add multiple target compounds, using a text box, and a button to add a new target
    # compound with name and m/z
    tk.Label(window, text="Target cmpds:").grid(row=2, column=0, sticky='nsew')
    target_cmpds = tk.Entry(window)
    target_cmpds.insert(tk.END, "name1:mz1;name2:mz2")
    target_cmpds.grid(row=2, column=1, sticky='nsew')
    # how
    tk.Label(window, text="How:").grid(row=3, column=0, sticky='nsew')
    how = tk.Entry(window)
    how.insert(tk.END, "data['int_name1'].sum() / (data['int_name1'].sum() + data['int_name2'].sum())")
    how.grid(row=3, column=1, sticky='nsew')
    # add a button to automatically generate the how string, by parsing the name1 and name2 from the target_cmpds, clear
    # the text box first, then insert the generated how string
    tk.Button(window, text="Generate",
              command=lambda: [how.delete(0, tk.END),
                               how.insert(tk.END,
                                          f"data['int_{target_cmpds.get().split(';')[0].split(':')[0]}'].sum() / "
                                          f"(data['int_{target_cmpds.get().split(';')[0].split(':')[0]}'].sum() +"
                                          f"data['int_{target_cmpds.get().split(';')[1].split(':')[0]}'].sum())")]).grid(
        row=3, column=2, sticky='nsew')
    # tol
    tk.Label(window, text="Tol (Da):").grid(row=4, column=0, sticky='nsew')
    tol = tk.Entry(window)
    tol.insert(tk.END, "0.01")
    tol.grid(row=4, column=1, sticky='nsew')
    # min_snr
    tk.Label(window, text="Min snr:").grid(row=5, column=0, sticky='nsew')
    min_snr = tk.Entry(window)
    min_snr.insert(tk.END, "1")
    min_snr.grid(row=5, column=1, sticky='nsew')
    # min_int
    tk.Label(window, text="Min int:").grid(row=6, column=0, sticky='nsew')
    min_int = tk.Entry(window)
    min_int.insert(tk.END, "10000")
    min_int.grid(row=6, column=1, sticky='nsew')
    # min_n_samples
    tk.Label(window, text="Min-n-spots/horizon:").grid(row=7, column=0, sticky='nsew')
    min_n_samples = tk.Entry(window)
    min_n_samples.insert(tk.END, "10")
    min_n_samples.grid(row=7, column=1, sticky='nsew')

    # horizon size
    tk.Label(window, text="Horizon size (μm):").grid(row=8, column=0, sticky='nsew')
    horizon_size = tk.Entry(window)
    horizon_size.insert(tk.END, "500")
    horizon_size.grid(row=8, column=1, sticky='nsew')

    # save results to a csv file
    tk.Label(window, text="Save 2D to:").grid(row=9, column=0, sticky='nsew')
    save_path = tk.Entry(window)
    save_path.insert(tk.END, "2D_res.csv")
    save_path.grid(row=9, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: [save_path.delete(0, tk.END),
                               save_path.insert(tk.END, filedialog.asksaveasfilename())]).grid(row=9, column=2,
                                                                                               sticky='nsew')

    # save 1d depth profile to a csv file
    tk.Label(window, text="Save 1D to:").grid(row=10, column=0, sticky='nsew')
    save_path_1d = tk.Entry(window)
    save_path_1d.insert(tk.END, "1D_res.csv")
    save_path_1d.grid(row=10, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: [save_path_1d.delete(0, tk.END),
                               save_path_1d.insert(tk.END, filedialog.asksaveasfilename())]).grid(row=10, column=2,
                                                                                                  sticky='nsew')
    # Only rows with Entry widgets get expanded
    for i in range(3):
        window.grid_columnconfigure(i, weight=1 if i == 1 else 0)  # Only the column with Entry widgets gets expanded

    # a button to start the calculation
    tk.Button(window, text="Start",
              command=lambda: get_depth_profile_from_gui(exported_txt_path.get(), sqlite_db_path.get(),
                                                         target_cmpds.get(),
                                                         how.get(), tol.get(), min_snr.get(), min_int.get(),
                                                         min_n_samples.get(),
                                                         horizon_size.get(), save_path.get(), save_path_1d.get())).grid(
        row=11, column=0, columnspan=3, sticky='nsew')


    # add another button to stitch the 1d downcore profiles together
    tk.Button(window, text="Stitch 1D", command=lambda: stitch_1d()).grid(row=12, column=0, columnspan=3, sticky='nsew')

def stitch_1d():
    # ask for the 1d downcore profiles
    file_paths = filedialog.askopenfilenames()
    # ask for the save path
    save_path = filedialog.asksaveasfilename()
    # stitch the 1d downcore profiles together
    import pandas as pd
    dfs = [pd.read_csv(file_path) for file_path in file_paths]
    df = pd.concat(dfs, axis=0, ignore_index=True)
    df.to_csv(save_path, index=False)
    # pop up a window to show it is done
    window = tk.Toplevel()
    window.title("Stitch 1D")
    text = tk.Text(window)
    text.insert(tk.END, f"1D downcore profiles have been stitched together and saved to {save_path}")
    text.pack()
    # add a ok button to close the window
    tk.Button(window, text="OK", command=window.destroy).pack()
    window.mainloop()

