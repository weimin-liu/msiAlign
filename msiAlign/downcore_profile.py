import re
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Combobox

from scripts.to1d import get_depth_profile_from_gui


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
              command=lambda: exported_txt_path.insert(tk.END,
                                                       ';'.join(filedialog.askopenfilenames(title='Select exported txt',
                                                                                            filetypes=[(
                                                                                                       "Plain text files",
                                                                                                       "*.txt")])) + ';')).grid(
        row=0, column=2, sticky='nsew')
    # sqlite_db_path
    tk.Label(window, text="Sqlite db path:").grid(row=1, column=0, sticky='nsew')
    sqlite_db_path = tk.Entry(window)
    sqlite_db_path.grid(row=1, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: sqlite_db_path.insert(tk.END, filedialog.askopenfilename(
                  title='Select sqlite db', filetypes=[("SQLite files", "*.db")]
              ))).grid(row=1, column=2,
                       sticky='nsew')

    # target_cmpds, able to add multiple target compounds, using a text box, and a button to add a new target
    # compound with name and m/z
    tk.Label(window, text="Target cmpds:").grid(row=2, column=0, sticky='nsew')
    target_cmpds = Combobox(window)
    target_cmpds.grid(row=2, column=1, sticky='nsew')
    target_cmpds['values'] = ("name1:mz1;name2:mz2",
                              "GDGT0:1324.3046;GDGT5:1314.2264",
                              "ALK37_2:553.5319;ALK37_3:551.5162")
    target_cmpds.current(0)

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
    tk.Label(window, text="Tol (Da, full window):").grid(row=4, column=0, sticky='nsew')
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
                               save_path.insert(tk.END, filedialog.asksaveasfilename(
                                   title="Save 2d result as", filetypes=[("CSV file", '*.csv')]
                               ))]).grid(row=9, column=2, sticky='nsew')

    # save 1d depth profile to a csv file
    tk.Label(window, text="Save 1D to:").grid(row=10, column=0, sticky='nsew')
    save_path_1d = tk.Entry(window)
    save_path_1d.insert(tk.END, "1D_res.csv")
    save_path_1d.grid(row=10, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: [save_path_1d.delete(0, tk.END),
                               save_path_1d.insert(tk.END, filedialog.asksaveasfilename(
                                   title="Save 1d result as", filetypes=[("CSV file", '*.csv')]
                               ))]).grid(row=10, column=2, sticky='nsew')
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


def calc_xrf_depth_profile():
    """Calculate the depth profile"""
    # popup a window to ask for the parameters
    window = tk.Toplevel()
    # pack the window
    window.title("Calc Downcore Profile (xrf)")
    # ask for the parameters
    # exported_txt_path, using file selection dialog, left is the text, right is the button for file selection
    tk.Label(window, text="Transformed csv path(s):").grid(row=0, column=0, sticky='nsew')

    exported_txt_path = tk.Entry(window)
    exported_txt_path.grid(row=0, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: exported_txt_path.insert(tk.END,
                                                       ';'.join(filedialog.askopenfilenames(title='Select transformed csv',
                                                                                            filetypes=[(
                                                                                                       "Plain text files",
                                                                                                       "*.csv")])) + ';')).grid(
        row=0, column=2, sticky='nsew')
    # how
    tk.Label(window, text="Ratios (sep by ','):").grid(row=3, column=0, sticky='nsew')
    how = tk.Entry(window)
    how.insert(tk.END, "Ca/Ti,Fe/Ti")
    how.grid(row=3, column=1, sticky='nsew')

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

    # save 1d depth profile to a csv file
    tk.Label(window, text="Save 1D to:").grid(row=10, column=0, sticky='nsew')
    save_path_1d = tk.Entry(window)
    save_path_1d.insert(tk.END, "1D_res.csv")
    save_path_1d.grid(row=10, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: [save_path_1d.delete(0, tk.END),
                               save_path_1d.insert(tk.END, filedialog.asksaveasfilename(
                                   title="Save 1d result as", filetypes=[("CSV file", '*.csv')]
                               ))]).grid(row=10, column=2, sticky='nsew')
    # Only rows with Entry widgets get expanded
    for i in range(3):
        window.grid_columnconfigure(i, weight=1 if i == 1 else 0)  # Only the column with Entry widgets gets expanded

    # a button to start the calculation
    tk.Button(window, text="Start",
              command=lambda: get_depth_profile_from_gui(exported_txt_path.get(), None, None,
                                                         how.get(), None, None, None,
                                                         min_n_samples.get(),
                                                         horizon_size.get(), None, save_path_1d.get())).grid(
        row=11, column=0, columnspan=3, sticky='nsew')

    # add another button to stitch the 1d downcore profiles together
    tk.Button(window, text="Stitch 1D", command=lambda: stitch_1d()).grid(row=12, column=0, columnspan=3, sticky='nsew')


def stitch_1d():
    # ask for the 1d downcore profiles
    file_paths = filedialog.askopenfilenames(title="Select 1D downcore profiles", filetypes=[("CSV files", "*.csv")])
    # ask for the save path
    save_path = filedialog.asksaveasfilename(title="Save 1D downcore profiles as", filetypes=[("CSV files", "*.csv")])
    # stitch the 1d downcore profiles together
    import pandas as pd
    dfs = [pd.read_csv(file_path) for file_path in file_paths]
    df = pd.concat(dfs, axis=0, ignore_index=True)
    df.to_csv(save_path, index=False)
    messagebox.showinfo("Stitch 1D", f"1D downcore profiles have been stitched together and saved to {save_path}")
