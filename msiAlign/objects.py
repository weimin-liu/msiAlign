import logging
import os
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox

from PIL import Image, ImageTk

Image.MAX_IMAGE_PIXELS = None


class LoadedImage:
    """A superclass for the loaded images"""

    def __init__(self):
        self.img_path = None
        self.img = None
        self.thumbnail = None
        self.thumbnail_size = (500, 500)  # the size of the thumbnail on the canvas
        self.tk_img = None
        self._tag = None
        self.locked = False
        self.origin = (0, 0)  # the origin of the image on the canvas

    @property
    def x(self):
        return self.origin[0]

    @property
    def y(self):
        return self.origin[1]

    @property
    def tag(self):
        return self._tag

    def __str__(self):
        return self.img_path

    def __repr__(self):
        return self.img_path

    @classmethod
    def from_path(cls, img_path):
        self = cls()
        self.img_path = img_path
        self._tag = os.path.basename(img_path)
        self.img = Image.open(img_path)
        self.thumbnail = self.img.copy()
        self.thumbnail.thumbnail(self.thumbnail_size)
        self.tk_img = ImageTk.PhotoImage(self.thumbnail)
        return self

    def create_im_on_canvas(self, app):
        # create the image on the canvas
        app.canvas.create_image(
            self.origin[0],
            self.origin[1],
            anchor="nw",
            image=self.tk_img,
            tags=f"{self.tag}"
        )
        # bind events to the image
        app.bind_events_to_loaded_images(self)

    def resize(self, size):
        self.thumbnail_size = size
        self.thumbnail = self.img.copy()
        self.thumbnail.thumbnail(size)
        self.tk_img = ImageTk.PhotoImage(self.thumbnail)

    def enlarge(self, scale_factor):
        self.thumbnail_size = (
            self.thumbnail.width * scale_factor,
            self.thumbnail.height * scale_factor
        )
        self.thumbnail = self.img.copy()
        self.thumbnail.thumbnail(self.thumbnail_size)
        self.tk_img = ImageTk.PhotoImage(self.thumbnail)

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def to_json(self):
        logging.debug(f"Saving {self.__class__.__name__} to json")
        json_data = {
            "type": self.__class__.__name__,
            "img_path": self.img_path,
            "thumbnail_size": self.thumbnail_size,
            "origin": self.origin,
            "locked": self.locked,
        }
        return json_data

    @classmethod
    def from_json(cls, json_data, app):
        self = cls()
        self.img_path = json_data['img_path']
        self.thumbnail_size = json_data['thumbnail_size']
        self.origin = json_data['origin']
        self.locked = json_data['locked']
        self.img = Image.open(self.img_path)
        self.thumbnail = self.img.copy()
        self.thumbnail.thumbnail(self.thumbnail_size)
        self.tk_img = ImageTk.PhotoImage(self.thumbnail)
        self._tag = os.path.basename(self.img_path)
        self.create_im_on_canvas(app)
        return self

    def rm(self, app):
        pass


def draw_teaching_points(x, y, app, size=3, img_tag=None):
    # mark the teaching point on the canvas
    app.canvas.create_oval(
        x - size,
        y - size,
        x + size,
        y + size,
        fill="red",
        tags=f"tp_{int(x)}_{int(y)}"
    )
    # bundle the teaching point with the image
    if img_tag is not None:
        app.canvas.addtag_withtag(img_tag, f"tp_{int(x)}_{int(y)}")


    # bind events to the teaching point
    if sys.platform == "darwin":
        app.canvas.tag_bind(f"tp_{int(x)}_{int(y)}",
                            "<Button-2>",
                            lambda e: app.right_click_on_tp.show_menu(e, f"tp_{int(x)}_{int(y)}"))
    elif sys.platform == "win32":
        app.canvas.tag_bind(f"tp_{int(x)}_{int(y)}",
                            "<Button-3>",
                            lambda e: app.right_click_on_tp.show_menu(e, f"tp_{int(x)}_{int(y)}"))
    else:
        raise Exception("Unsupported platform")

    # return the tag of the teaching point
    return f"tp_{int(x)}_{int(y)}"


class TeachableImage(LoadedImage):
    """A subclass of LoadedImage that holds the teachable images"""

    def __init__(self):
        super().__init__()
        self.teaching_points = None  # a list of teaching points
        self.tp_size = 3  # the size of the teaching point on the canvas
        self.flipped = False

    @property
    def label_indexed_teaching_points(self):
        if self.teaching_points is not None:
            try:
                return {v[3]: v[:3] for v in self.teaching_points.values()}
            except IndexError:
                return None
        else:
            return None

    @property
    def px_teaching_points_labels(self):
        if self.teaching_points is not None:
            try:
                return {k: v[3] for k, v in self.teaching_points.items()}
            except IndexError:
                return None
        else:
            return None

    def show_tp_labels(self, app):
        if self.teaching_points is not None:
            for k, v in self.teaching_points.items():
                try:
                    text = tk.Text(app.canvas, height=1, width=3)
                    text.insert(tk.END, v[3])
                    text.config(state=tk.DISABLED)
                    app.canvas.create_window(
                        k[0],
                        k[1],
                        window=text,
                        anchor="nw",
                        tags=f"tp_labels"
                    )
                except IndexError:
                    pass

    def flip(self):
        self.img = self.img.transpose(Image.FLIP_TOP_BOTTOM)
        self.thumbnail = self.img.copy()
        self.thumbnail.thumbnail(self.thumbnail_size)
        self.tk_img = ImageTk.PhotoImage(self.thumbnail)
        self.flipped = not self.flipped

    def update_teaching_points_on_resize(self, app, origin, scale_factor):
        logging.debug(f"origin: {origin}, scale_factor: {scale_factor}")
        logging.debug(f"teaching points: {self.teaching_points}")
        # calculate the new teaching points coordinates after image resize
        new_keys = []
        old_keys = []
        if self.teaching_points is not None:
            for k, v in self.teaching_points.items():
                old_keys.append(k)
                x, y = k
                app.canvas.delete(f"tp_{int(x)}_{int(y)}")
                x = origin[0] + (x - origin[0]) * scale_factor
                y = origin[1] + (y - origin[1]) * scale_factor
                new_keys.append((x, y))
                draw_teaching_points(x, y, app, size=self.tp_size, img_tag=self.tag)
            for old_key, new_key in zip(old_keys, new_keys):
                self.teaching_points[new_key] = self.teaching_points.pop(old_key)

    def update_teaching_points(self, app, offset_x, offset_y):
        old_keys = []
        new_keys = []
        if self.teaching_points is not None:
            for k, v in self.teaching_points.items():
                x, y = k
                old_keys.append(k)
                app.canvas.delete(f"tp_{int(x)}_{int(y)}")
                x += offset_x
                y += offset_y
                new_keys.append((x, y))
                # remove the teaching point from the canvas
                draw_teaching_points(x, y, app, size=self.tp_size, img_tag=self.tag)
            for old_key, new_key in zip(old_keys, new_keys):
                self.teaching_points[new_key] = self.teaching_points.pop(old_key)

    def add_teaching_point(self, event, app):
        canvas_x, canvas_y = app.canvas.canvasx(event.x), app.canvas.canvasy(event.y)
        logging.debug(f"teaching point added canvas_x: {canvas_x}, canvas_y: {canvas_y}")
        # draw the teaching point on the canvas
        draw_teaching_points(canvas_x, canvas_y, app, size=self.tp_size, img_tag=self.tag)

        # try to find the approximate depth of the teaching point
        if app.sediment_start is not None and app.cm_per_pixel is not None:
            depth = abs(app.canvas.coords(app.sediment_start)[0] - canvas_x) * app.cm_per_pixel
        else:
            depth = None

        original_width, original_height = self.img.size
        scale_x = original_width / self.thumbnail.width
        scale_y = original_height / self.thumbnail.height

        if not self.flipped:
            # calculate the coordinates of the teaching point in the original image
            img_x = (canvas_x - self.x) * scale_x
            img_y = (canvas_y - self.y) * scale_y
        else:
            img_x = (canvas_x - self.x) * scale_x
            img_y = (self.y + self.thumbnail.height - canvas_y) * scale_y

        if self.teaching_points is None:
            self.teaching_points = {}
        teaching_point_key = (canvas_x, canvas_y)
        self.teaching_points[teaching_point_key] = (img_x, img_y, depth)
        # if it is an MSI image, update the teaching point coordinates in the MSI image
        try:
            self.teaching_points_px_coords[teaching_point_key] = (img_x, img_y, depth)
        except Exception as e:
            logging.error(e)
            pass

    def to_json(self):
        json_data = super().to_json()
        json_data["flipped"] = self.flipped
        json_data["teaching_points"] = self.teaching_points
        # json data key cannot be a tuple, convert the key to a string
        try:
            json_data["teaching_points"] = {str(k): v for k, v in json_data["teaching_points"].items()}
        except Exception as e:
            logging.error(e)
            pass
        logging.debug(f"json data to write: {json_data}")
        return json_data

    @classmethod
    def from_json(cls, json_data, app):
        self = super().from_json(json_data, app)
        logging.debug(f"class: {self.__class__.__name__}")
        # convert the key back to a tuple
        try:
            json_data["teaching_points"] = {eval(k): v for k, v in json_data["teaching_points"].items()}
            self.teaching_points = json_data['teaching_points']
            logging.debug(f"teaching points: {self.teaching_points}")
        except KeyError:
            self.teaching_points = None
        try:
            self.flipped = json_data['flipped']
            if self.flipped:
                self.flipped = False
                self.flip()
                app.canvas.itemconfig(self.tag, image=self.tk_img)
        except Exception as e:
            logging.error(e)
            pass
        # draw the teaching points on the canvas if they exist
        try:
            if self.teaching_points is not None:
                for tp, _ in self.teaching_points.items():
                    draw_teaching_points(tp[0], tp[1], app, size=self.tp_size, img_tag=self.tag)
        except Exception as e:
            logging.error(e)
            pass
        return self


class MsiImage(TeachableImage):
    """A subclass of LoadedImage that holds the MSI image"""

    def __init__(self):
        super().__init__()
        self.msi_rect = None  # the coordinates of the MSI image rectangle in R00X?Y? format
        self.px_rect = None  # the coordinates of the MSI image rectangle in pixel
        self.teaching_points_px_coords = {}  # the coordinates of the teaching points in the MSI image

    def update_tp_coords(self, sqlite_db_path):
        """ replace the coordinates of the teaching points with the MSI coordinates"""
        # copy the values to px_coords when this command is first called
        if self.teaching_points_px_coords is None:
            self.teaching_points_px_coords = self.teaching_points.copy()
        if self.msi_rect is None or self.px_rect is None:
            # if the MSI and pixel rectangle are not set, try reading the coordinates from the metadata
            import sqlite3
            conn = sqlite3.connect(sqlite_db_path)
            c = conn.cursor()
            # get the image name, px_rect, and msi_rect
            c.execute('SELECT msi_img_file_name, px_rect, msi_rect FROM metadata')
            data = c.fetchall()
            for row in data:
                im_name, px_rect, msi_rect = row
                if im_name == os.path.basename(self.img_path):
                    self.px_rect = eval(px_rect)
                    self.msi_rect = eval(msi_rect)
                    break
                logging.debug(f"{im_name} not found in the metadata")
            conn.close()
        assert self.msi_rect is not None and self.px_rect is not None, (
            messagebox.showerror("Error","Something went wrong, please check the metadata file"))
        assert self.teaching_points is not None, messagebox.showerror("Error","No teaching points found")
        logging.debug(f"msi_rect: {self.msi_rect}")
        logging.debug(f"px_rect: {self.px_rect}")
        x_min, y_min, x_max, y_max = self.msi_rect
        x_min_px, y_min_px, x_max_px, y_max_px = self.px_rect
        for k, v in self.teaching_points_px_coords.items():
            msi_x = (v[0] - x_min_px) / (x_max_px - x_min_px) * (x_max - x_min) + x_min
            msi_y = (v[1] - y_min_px) / (y_max_px - y_min_px) * (y_max - y_min) + y_min
            try:
                self.teaching_points[k] = (msi_x, msi_y, v[2], v[3])
            except IndexError:
                self.teaching_points[k] = (msi_x, msi_y, v[2])


    def to_json(self):
        json_data = super().to_json()
        json_data["msi_rect"] = self.msi_rect
        json_data["px_rect"] = self.px_rect
        if self.teaching_points_px_coords is not None:
            json_data["teaching_points_px_coords"] = self.teaching_points_px_coords
            json_data["teaching_points_px_coords"] = {str(k): v for k, v in
                                                      json_data["teaching_points_px_coords"].items()}
        return json_data

    @classmethod
    def from_json(cls, json_data, app):
        self = super().from_json(json_data, app)
        self.msi_rect = json_data['msi_rect']
        self.px_rect = json_data['px_rect']
        try:
            json_data["teaching_points_px_coords"] = {eval(k): v for k, v in
                                                      json_data["teaching_points_px_coords"].items()}
            self.teaching_points_px_coords = json_data['teaching_points_px_coords']
        except Exception as e:
            logging.error(e)
            pass
        return self

    def rm(self, app):
        f = simpledialog.askstring("Remove MSI Image", "Are you sure you want to remove the MSI image? (Y/N)")
        if f.lower() == "y":
            # remove the image from the canvas
            app.canvas.delete(self.tag)
            # remove from the items dictionary
            del app.items[self.tag]
        else:
            return


class LinescanImage(LoadedImage):
    """A subclass of LoadedImage that holds the linescan image"""

    def __init__(self):
        super().__init__()

    def rm(self, app):
        f = simpledialog.askstring("Remove Linescan Image", "Are you sure you want to remove the linescan image? (Y/N)")
        if f.lower() == "y":
            # remove the image from the canvas
            app.canvas.delete(self.tag)
            # remove from the items dictionary
            del app.items[self.tag]
            app.n_linescan -= 1
        else:
            return


class XrayImage(TeachableImage):
    """A subclass of LoadedImage that holds the xray image"""

    def __init__(self):
        super().__init__()

    def rm(self, app):
        f = simpledialog.askstring("Remove Xray Image", "Are you sure you want to remove the xray image? (Y/N)")
        if f.lower() == "y":
            # remove the image from the canvas
            app.canvas.delete(self.tag)
            # remove from the items dictionary
            del app.items[self.tag]
            app.n_xray -= 1
        else:
            return


class VerticalLine:
    color_map = {
        "scale_line": "blue",
        "sediment_start_line": "green"
    }

    def __init__(self, position):
        self.position = position
        self.depth = None
        self._tag = f"vl_{position[0]}"
        self.type = "VerticalLine"

    @property
    def tag(self):
        return self._tag

    def create_on_canvas(self, app):
        app.canvas.create_line(
            self.position[0],
            0,
            self.position[0],
            5000,
            fill=self.color,
            tags=self.tag,
            width=1,
            dash=(4, 4)
        )
        app.bind_events_to_vertical_lines(self)

    def add_depth_text(self, app, depth):
        self.depth = depth
        text = tk.Text(app.canvas, height=1, width=8)
        text.insert(tk.END, f"{depth}cm")
        text.config(state=tk.DISABLED)
        app.canvas.create_window(
            self.position[0],
            10,
            window=text,
            anchor="nw",
            tags=self.tag
        )

    @property
    def x(self):
        return self.position[0]

    @property
    def y(self):
        return self.position[1]

    @property
    def color(self):
        if self.tag in self.color_map:
            return self.color_map[self.tag]
        else:
            return "red"

    def __str__(self):
        return self.tag

    def __repr__(self):
        return self.tag

    def rm(self, app):
        # remove the teaching point from the canvas
        app.canvas.delete(self.tag)
        # remove from the items dictionary
        del app.items[self.tag]

    @classmethod
    def from_json(cls, json_data, app):
        self = cls(json_data['position'])
        self._tag = json_data['tag']
        self.depth = json_data['depth']
        self.create_on_canvas(app)
        return self

    def to_json(self):
        return {
            "type": "VerticalLine",
            "tag": self.tag,
            "position": self.position,
            "depth": self.depth,
        }


if __name__ == "__main__":
    pass
