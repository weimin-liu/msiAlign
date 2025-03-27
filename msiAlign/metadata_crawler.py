""" crawler for metadata """
import os
import shutil
# create a namedtuple for the metadata
from collections import namedtuple
from tkinter import filedialog, simpledialog, messagebox
from msiAlign.func import get_image_file_from_mis, get_px_rect_from_mis, get_msi_rect_from_imaginginfo

Metadata = namedtuple("Metadata", ["spec_file_name",
                                   "msi_img_file_path",
                                   "msi_img_file_name",
                                   "px_rect",
                                   "msi_rect",
                                   "spot_name",
                                   "TIC",
                                   "maxpeak",
                                   "rt"])


class MetadataCrawler:
    """Crawl the metadata directory and return the metadata files"""

    def __init__(self, metadata_dir):
        self.metadata_dir = metadata_dir
        self.metadata = {}
        # make sure the subdirectories are something ending with '.i'
        self.idir = [subdir for subdir in os.listdir(metadata_dir) if subdir.endswith(".i")]
        assert len(self.idir) > 0, "No .i subdirectories found"

    def crawl(self):
        # craw the metadata under .i subdirectories
        # get all the .mis files under the .i subdirectories
        for subdir in self.idir:
            for root, dirs, files in os.walk(os.path.join(self.metadata_dir, subdir)):
                for file in files:
                    if file.endswith(".mis"):
                        mis_file = os.path.join(root, file)
                        # infer the spec file name from the mis file
                        spec_file_name = mis_file.replace(".mis", ".d")
                        if os.path.exists(spec_file_name):
                            try:
                                px_rect = get_px_rect_from_mis(mis_file)
                                xml_file = os.path.join(root, spec_file_name, "ImagingInfo.xml")
                                msi_rect, spot_name, tic, maxpeak, rt = get_msi_rect_from_imaginginfo(xml_file, return_spot_name=True)
                                im_name = get_image_file_from_mis(mis_file)
                                im_file_path = os.path.join(root, im_name)
                                assert im_name not in self.metadata.keys(), 'duplicate entries found'
                                self.metadata[os.path.basename(spec_file_name)] = Metadata(
                                    spec_file_name=os.path.basename(spec_file_name),
                                    msi_img_file_path=im_file_path,
                                    msi_img_file_name=im_name,
                                    px_rect=px_rect,
                                    msi_rect=msi_rect,
                                    spot_name=spot_name,
                                    TIC=tic,
                                    maxpeak=maxpeak,
                                    rt=rt)
                            except ValueError:
                                continue

    def to_sqlite(self, db_path):
        # create a sqlite database if it does not exist
        if not os.path.exists(db_path):
            open(db_path, 'w').close()
        else:
            os.remove(db_path)
            open(db_path, 'w').close()
        # write the metadata to the sqlite database
        import sqlite3
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            'CREATE TABLE IF NOT EXISTS metadata (spec_id INTEGER PRIMARY KEY, spec_file_name TEXT, msi_img_file_path TEXT, '
            'msi_img_file_name TEXT, px_rect TEXT, msi_rect TEXT, spot_name TEXT, TIC TEXT, maxpeak TEXT, rt TEXT)')
        for k, v in self.metadata.items():
            c.execute(
                'INSERT INTO metadata (spec_file_name, msi_img_file_path, msi_img_file_name, px_rect, msi_rect, spot_name, TIC, maxpeak, rt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (v.spec_file_name, v.msi_img_file_path,
                 v.msi_img_file_name,
                 str(list(int(i) for i in v.px_rect)),
                 str(list(int(i) for i in v.msi_rect)),
                 str(v.spot_name),
                 str(v.TIC),
                 str(v.maxpeak),
                 str(v.rt)))
        conn.commit()
        conn.close()

    def collect_msi_img(self, target_dir):
        assert len(self.metadata) > 0, "No metadata found"
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        for k, v in self.metadata.items():
            # copy the msi image to the target directory
            shutil.copy(v.msi_img_file_path, os.path.join(target_dir, v.msi_img_file_name))


def crawl_metadata():
    """Crawl the raw data directory and return the metadata files"""
    metadata_dir = filedialog.askdirectory(title="Select the raw data directory")
    if metadata_dir:
        metadata_crawler = MetadataCrawler(metadata_dir)
        metadata_crawler.crawl()
        # ask the user to save the metadata to a sqlite database
        db_path = filedialog.asksaveasfilename(title="Save Metadata to SQLite Database",
                                               defaultextension=".db",
                                               filetypes=[("SQLite Database", "*.db")])
        if db_path:
            metadata_crawler.to_sqlite(db_path)
        # ask the user if they want to collect the msi images
        collect_msi_img = simpledialog.askstring("Collect MSI Images",
                                                 "Do you want to collect the MSI images? (y/n)")
        if collect_msi_img == "y":
            target_dir = filedialog.askdirectory(title="Select the target directory to collect MSI images")
            if target_dir:
                metadata_crawler.collect_msi_img(target_dir)
                messagebox.showinfo(
                    title="Success",
                    message=f"MSI images have been collected to {target_dir}")
            else:
                messagebox.showerror("No target directory is given")

    else:
        messagebox.showerror(
            title="Error",
            message="No raw data directory is selected")
        return


if __name__ == "__main__":
    pass
