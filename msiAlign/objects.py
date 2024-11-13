import os
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox
import numpy as np

from PIL import Image, ImageTk

Image.MAX_IMAGE_PIXELS = None


def get_right_click_event():
    return "<Button-2>" if sys.platform == "darwin" else "<Button-3>"


def key_to_str(key):
    return f"{key[0]},{key[1]}"


def str_to_key(s):
    x_str, y_str = s.split(",")
    return float(x_str), float(y_str)


def draw_teaching_points(x, y, app, size=3, img_tag=None):
    tp_tag = f"tp_{int(x)}_{int(y)}"

    app.canvas.create_oval(
        x - size,
        y - size,
        x + size,
        y + size,
        fill="red",
        tags=tp_tag
    )
    if img_tag is not None:
        app.canvas.addtag_withtag(img_tag, tp_tag)

    app.canvas.tag_bind(tp_tag,
                        get_right_click_event(),
                        lambda e: app.right_click_on_tp.show_menu(e, tp_tag))

    return tp_tag


class LoadedImage:
    """A superclass for the loaded images"""

    def __init__(self):
        self.img_path = None
        self.img = None
        self.thumbnail = None
        self.thumbnail_size = (500, 500)
        self.tk_img = None
        self._tag = None
        self.locked = False
        self.origin = (None, None)

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

    def load_image(self):
        self.img = Image.open(self.img_path)
        self.update_thumbnail()

    def update_thumbnail(self):
        self.thumbnail = self.img.copy()
        self.thumbnail.thumbnail(self.thumbnail_size)
        self.tk_img = ImageTk.PhotoImage(self.thumbnail)

    @classmethod
    def from_path(cls, img_path):
        self = cls()
        self.img_path = img_path
        self._tag = os.path.basename(img_path).replace(" ", "_")
        self.load_image()
        return self

    def create_im_on_canvas(self, app):
        if self.origin == (None, None):
            x = app.canvas.canvasx(app.canvas.winfo_width() / 2)
            y = app.canvas.canvasy(app.canvas.winfo_height() / 2)
            self.origin = (x - self.thumbnail.width / 2, y - self.thumbnail.height / 2)

        app.canvas.create_image(
            self.origin[0],
            self.origin[1],
            anchor="nw",
            image=self.tk_img,
            tags=self.tag
        )
        app.bind_events_to_loaded_images(self)

    def resize(self, size):
        self.thumbnail_size = size
        self.update_thumbnail()

    def enlarge(self, scale_factor):
        self.thumbnail_size = (
            self.thumbnail.width * scale_factor,
            self.thumbnail.height * scale_factor
        )
        self.update_thumbnail()

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def to_json(self):
        return {
            "type": self.__class__.__name__,
            "img_path": self.img_path,
            "thumbnail_size": self.thumbnail_size,
            "origin": self.origin,
            "locked": self.locked,
        }

    @classmethod
    def from_json(cls, json_data, app):
        self = cls()
        self.img_path = json_data['img_path']
        self.thumbnail_size = tuple(json_data['thumbnail_size'])
        self.origin = tuple(json_data['origin'])
        self.locked = json_data['locked']
        self._tag = os.path.basename(self.img_path).replace(" ", "_")
        self.load_image()
        self.create_im_on_canvas(app)
        return self

    def rm(self, app):
        if messagebox.askyesno("Remove Image", "Are you sure you want to remove this image?"):
            app.canvas.delete(self.tag)
            del app.items[self.tag]


class TeachableImage(LoadedImage):
    """A subclass of LoadedImage that holds the teachable images"""

    def __init__(self):
        super().__init__()
        self.teaching_points_px_coords = {}
        self.teaching_points = {}
        self.tp_size = 3
        self.show_sediment_start_line_not_set_warning = True

    @property
    def label_indexed_teaching_points(self):
        return {v[3]: v[:3] for v in self.teaching_points.values() if len(v) >= 4}

    @property
    def px_teaching_points_labels(self):
        return {k: v[3] for k, v in self.teaching_points.items() if len(v) >= 4}

    def show_tp_labels(self, app):
        for k, v in self.teaching_points.items():
            if len(v) >= 4:
                label = v[3]
                text = tk.Text(app.canvas, height=1, width=3)
                text.insert(tk.END, label)
                text.config(state=tk.DISABLED)
                app.canvas.create_window(
                    k[0],
                    k[1],
                    window=text,
                    anchor="nw",
                    tags="tp_labels"
                )

    def _update_teaching_points(self, app, transform_func):
        old_keys = list(self.teaching_points.keys())
        for old_key in old_keys:
            x, y = old_key
            app.canvas.delete(f"tp_{int(x)}_{int(y)}")
            x_new, y_new = transform_func(x, y)
            new_key = (x_new, y_new)
            draw_teaching_points(x_new, y_new, app, size=self.tp_size, img_tag=self.tag)
            self.teaching_points[new_key] = self.teaching_points.pop(old_key)
            if self.teaching_points_px_coords:
                self.teaching_points_px_coords[new_key] = self.teaching_points_px_coords.pop(old_key)

    def update_teaching_points_on_resize(self, app, origin, scale_factor):
        self._update_teaching_points(
            app,
            lambda x, y: (
                origin[0] + (x - origin[0]) * scale_factor,
                origin[1] + (y - origin[1]) * scale_factor
            )
        )

    def update_teaching_points(self, app, offset_x, offset_y):
        self._update_teaching_points(
            app,
            lambda x, y: (x + offset_x, y + offset_y)
        )

    def add_teaching_point(self, event, app):
        canvas_x, canvas_y = app.canvas.canvasx(event.x), app.canvas.canvasy(event.y)
        draw_teaching_points(canvas_x, canvas_y, app, size=self.tp_size, img_tag=self.tag)

        if app.sediment_start is not None and app.cm_per_pixel is not None:
            depth = abs(app.canvas.coords(app.sediment_start)[0] - canvas_x) * app.cm_per_pixel
        else:
            if self.show_sediment_start_line_not_set_warning:
                messagebox.showwarning("Warning", "Sediment start line not found, depth not calculated.")
                self.show_sediment_start_line_not_set_warning = False
            depth = None

        original_width, original_height = self.img.size
        scale_x = original_width / self.thumbnail.width
        scale_y = original_height / self.thumbnail.height

        img_x = (canvas_x - self.x) * scale_x
        img_y = (canvas_y - self.y) * scale_y

        teaching_point_data = (img_x, img_y, depth)

        teaching_point_key = (canvas_x, canvas_y)
        self.teaching_points[teaching_point_key] = teaching_point_data
        self.teaching_points_px_coords[teaching_point_key] = teaching_point_data

    def to_json(self):
        json_data = super().to_json()
        json_data["teaching_points"] = {key_to_str(k): v for k, v in self.teaching_points.items()}
        json_data["teaching_points_px_coords"] = {key_to_str(k): v for k, v in self.teaching_points_px_coords.items()}
        return json_data

    @classmethod
    def from_json(cls, json_data, app):
        self = super().from_json(json_data, app)
        self.teaching_points = {str_to_key(k): v for k, v in json_data.get("teaching_points", {}).items()}
        for tp_key in self.teaching_points.keys():
            x, y = tp_key
            draw_teaching_points(x, y, app, size=self.tp_size, img_tag=self.tag)
        self.teaching_points_px_coords = {str_to_key(k): v for k, v in json_data.get("teaching_points_px_coords", {}).items()}
        if len(self.teaching_points_px_coords) == 0:
            self.teaching_points_px_coords = self.teaching_points.copy()
        return self


class MsiImage(TeachableImage):
    """A subclass of TeachableImage that holds the MSI image"""

    def __init__(self):
        super().__init__()
        self.msi_rect = None
        self.px_rect = None
        self.teaching_points_px_coords = {}

    def update_tp_coords(self, sqlite_db_path):
        if not self.teaching_points_px_coords:
            self.teaching_points_px_coords = self.teaching_points.copy()
        if self.msi_rect is None or self.px_rect is None:
            import sqlite3
            conn = sqlite3.connect(sqlite_db_path)
            c = conn.cursor()
            c.execute('SELECT msi_img_file_name, px_rect, msi_rect FROM metadata')
            data = c.fetchall()
            for row in data:
                im_name, px_rect, msi_rect = row
                if im_name == os.path.basename(self.img_path):
                    self.px_rect = eval(px_rect)
                    self.msi_rect = eval(msi_rect)
                    break
            conn.close()
        if self.msi_rect is None or self.px_rect is None:
            messagebox.showerror("Error", "Something went wrong, please check the metadata file")
            return
        if not self.teaching_points:
            messagebox.showerror("Error", "No teaching points found")
            return
        x_min, y_min, x_max, y_max = self.msi_rect
        x_min_px, y_min_px, x_max_px, y_max_px = self.px_rect
        for k, v in self.teaching_points_px_coords.items():
            msi_x = (v[0] - x_min_px) / (x_max_px - x_min_px) * (x_max - x_min) + x_min
            msi_y = (v[1] - y_min_px) / (y_max_px - y_min_px) * (y_max - y_min) + y_min
            self.teaching_points[k] = (msi_x, msi_y, *v[2:])

    def to_json(self):
        json_data = super().to_json()
        json_data["msi_rect"] = self.msi_rect
        json_data["px_rect"] = self.px_rect
        return json_data

    @classmethod
    def from_json(cls, json_data, app):
        self = super().from_json(json_data, app)
        self.msi_rect = tuple(json_data['msi_rect']) if json_data['msi_rect'] is not None else None
        self.px_rect = tuple(json_data['px_rect']) if json_data['px_rect'] is not None else None
        return self


class VerticalLine:
    color_map = {
        "scale_line": "blue",
        "sediment_start_line": "green"
    }

    def __init__(self, position, line_type=None):
        self.position = position
        self.depth = None
        self.line_type = line_type
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
        return self.color_map.get(self.line_type, "red")

    def __str__(self):
        return self.tag

    def __repr__(self):
        return self.tag

    def rm(self, app):
        app.canvas.delete(self.tag)
        del app.items[self.tag]

    @classmethod
    def from_json(cls, json_data, app):
        self = cls(json_data['position'], line_type=json_data.get('line_type'))
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
            "line_type": self.line_type
        }


if __name__ == "__main__":
    pass