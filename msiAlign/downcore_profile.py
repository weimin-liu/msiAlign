import re
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Combobox

from scripts.to1d import get_depth_profile_from_gui


def calc_depth_profile(analysis_type="MSI"):
    """Calculate the depth profile for either MSI or XRF data

    Args:
        analysis_type (str): Either "MSI" or "XRF" to determine which interface to show
    """
    # popup a window to ask for the parameters
    window = tk.Toplevel()
    window.title(f"Calc Downcore Profile ({analysis_type})")

    # Common widgets for both types
    current_row = 0

    if analysis_type == "MSI":
        # File selection for MSI
        tk.Label(window, text="Exported txt path(s):").grid(row=current_row, column=0, sticky='nsew')
        exported_txt_path = tk.Entry(window)
        exported_txt_path.grid(row=current_row, column=1, sticky='nsew')
        tk.Button(window, text="Select",
                  command=lambda: exported_txt_path.insert(tk.END,
                                                           ';'.join(
                                                               filedialog.askopenfilenames(title='Select exported txt',
                                                                                           filetypes=[
                                                                                               ("Plain text files",
                                                                                                "*.txt")])) + ';')).grid(
            row=current_row, column=2, sticky='nsew')
        current_row += 1

        # SQLite DB path
        tk.Label(window, text="Sqlite db path:").grid(row=current_row, column=0, sticky='nsew')
        sqlite_db_path = tk.Entry(window)
        sqlite_db_path.grid(row=current_row, column=1, sticky='nsew')
        tk.Button(window, text="Select",
                  command=lambda: sqlite_db_path.insert(tk.END, filedialog.askopenfilename(
                      title='Select sqlite db', filetypes=[("SQLite files", "*.db")]
                  ))).grid(row=current_row, column=2, sticky='nsew')
        current_row += 1

        # Target compounds
        tk.Label(window, text="Target cmpds:").grid(row=current_row, column=0, sticky='nsew')
        target_cmpds = Combobox(window)
        target_cmpds.grid(row=current_row, column=1, sticky='nsew')
        target_cmpds['values'] = ("name1:mz1;name2:mz2",
                                  "GDGT0:1324.3046;GDGT5:1314.2264",
                                  "ALK37_2:553.5319;ALK37_3:551.5162")
        target_cmpds.current(0)
        current_row += 1

        # How (calculation method)
        tk.Label(window, text="How:").grid(row=current_row, column=0, sticky='nsew')
        how = tk.Entry(window)
        how.insert(tk.END, "data['int_name1'].sum() / (data['int_name1'].sum() + data['int_name2'].sum())")
        how.grid(row=current_row, column=1, sticky='nsew')
        tk.Button(window, text="Generate",
                  command=lambda: [how.delete(0, tk.END),
                                   how.insert(tk.END,
                                              f"data['int_{target_cmpds.get().split(';')[0].split(':')[0]}'].sum() / "
                                              f"(data['int_{target_cmpds.get().split(';')[0].split(':')[0]}'].sum() +"
                                              f"data['int_{target_cmpds.get().split(';')[1].split(':')[0]}'].sum())")]).grid(
            row=current_row, column=2, sticky='nsew')
        current_row += 1

        # Additional MSI-specific parameters
        tk.Label(window, text="Tol (Da, full window):").grid(row=current_row, column=0, sticky='nsew')
        tol = tk.Entry(window)
        tol.insert(tk.END, "0.01")
        tol.grid(row=current_row, column=1, sticky='nsew')
        current_row += 1

        tk.Label(window, text="Min snr:").grid(row=current_row, column=0, sticky='nsew')
        min_snr = tk.Entry(window)
        min_snr.insert(tk.END, "1")
        min_snr.grid(row=current_row, column=1, sticky='nsew')
        current_row += 1

        tk.Label(window, text="Min int:").grid(row=current_row, column=0, sticky='nsew')
        min_int = tk.Entry(window)
        min_int.insert(tk.END, "10000")
        min_int.grid(row=current_row, column=1, sticky='nsew')
        current_row += 1

        # Save 2D results
        tk.Label(window, text="Save 2D to:").grid(row=current_row, column=0, sticky='nsew')
        save_path = tk.Entry(window)
        save_path.insert(tk.END, "2D_res.csv")
        save_path.grid(row=current_row, column=1, sticky='nsew')
        tk.Button(window, text="Select",
                  command=lambda: [save_path.delete(0, tk.END),
                                   save_path.insert(tk.END, filedialog.asksaveasfilename(
                                       title="Save 2d result as", filetypes=[("CSV file", '*.csv')]
                                   ))]).grid(row=current_row, column=2, sticky='nsew')
        current_row += 1

    else:  # XRF
        # File selection for XRF
        tk.Label(window, text="Transformed csv path(s):").grid(row=current_row, column=0, sticky='nsew')
        exported_txt_path = tk.Entry(window)
        exported_txt_path.grid(row=current_row, column=1, sticky='nsew')
        tk.Button(window, text="Select",
                  command=lambda: exported_txt_path.insert(tk.END,
                                                           ';'.join(filedialog.askopenfilenames(
                                                               title='Select transformed csv',
                                                               filetypes=[("Plain text files",
                                                                           "*.csv")])) + ';')).grid(
            row=current_row, column=2, sticky='nsew')
        current_row += 1

        # How (ratios)
        tk.Label(window, text="Ratios (sep by ';'):").grid(row=current_row, column=0, sticky='nsew')
        how = tk.Entry(window)
        how.insert(tk.END, "Ca/Ti;Fe/Ti")
        how.grid(row=current_row, column=1, sticky='nsew')
        current_row += 1

        # Set these to None for XRF
        sqlite_db_path = None
        target_cmpds = None
        tol = None
        min_snr = None
        min_int = None
        save_path = None

    # Common parameters for both types
    tk.Label(window, text="Min-n-spots/horizon:").grid(row=current_row, column=0, sticky='nsew')
    min_n_samples = tk.Entry(window)
    min_n_samples.insert(tk.END, "10")
    min_n_samples.grid(row=current_row, column=1, sticky='nsew')
    current_row += 1

    tk.Label(window, text="Horizon size (μm):").grid(row=current_row, column=0, sticky='nsew')
    horizon_size = tk.Entry(window)
    horizon_size.insert(tk.END, "500")
    horizon_size.grid(row=current_row, column=1, sticky='nsew')
    current_row += 1

    # Save 1D results
    tk.Label(window, text="Save 1D to:").grid(row=current_row, column=0, sticky='nsew')
    save_path_1d = tk.Entry(window)
    save_path_1d.insert(tk.END, "1D_res.csv")
    save_path_1d.grid(row=current_row, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: [save_path_1d.delete(0, tk.END),
                               save_path_1d.insert(tk.END, filedialog.asksaveasfilename(
                                   title="Save 1d result as", filetypes=[("CSV file", '*.csv')]
                               ))]).grid(row=current_row, column=2, sticky='nsew')
    current_row += 1

    # Configure grid
    for i in range(3):
        window.grid_columnconfigure(i, weight=1 if i == 1 else 0)

    # Start button
    tk.Button(window, text="Start",
              command=lambda: get_depth_profile_from_gui(exported_txt_path.get(),
                                                         sqlite_db_path,
                                                         target_cmpds.get() if target_cmpds else None,
                                                         how.get(),
                                                         tol.get() if tol else None,
                                                         min_snr.get() if min_snr else None,
                                                         min_int.get() if min_int else None,
                                                         min_n_samples.get(),
                                                         horizon_size.get(),
                                                         save_path.get() if save_path else None,
                                                         save_path_1d.get())).grid(
        row=current_row, column=0, columnspan=3, sticky='nsew')
    current_row += 1

    # Stitch button
    tk.Button(window, text="Stitch 1D", command=stitch_1d).grid(row=current_row, column=0, columnspan=3, sticky='nsew')


def stitch_1d():
    """Stitch multiple 1D depth profiles together"""
    file_paths = filedialog.askopenfilenames(title="Select 1D downcore profiles", filetypes=[("CSV files", "*.csv")])
    save_path = filedialog.asksaveasfilename(title="Save 1D downcore profiles as", filetypes=[("CSV files", "*.csv")])

    import pandas as pd
    dfs = [pd.read_csv(file_path) for file_path in file_paths]
    df = pd.concat(dfs, axis=0, ignore_index=True)
    df.to_csv(save_path, index=False)
    messagebox.showinfo("Stitch 1D", f"1D downcore profiles have been stitched together and saved to {save_path}")


def show_analysis_selector():
    """Show a dialog to select the analysis type"""
    window = tk.Toplevel()
    window.title("Select Analysis Type")

    tk.Label(window, text="Choose analysis type:").pack(pady=10)

    tk.Button(window, text="MSI Analysis",
              command=lambda: [window.destroy(), calc_depth_profile("MSI")]).pack(fill=tk.X, padx=20, pady=5)

    tk.Button(window, text="XRF Analysis",
              command=lambda: [window.destroy(), calc_depth_profile("XRF")]).pack(fill=tk.X, padx=20, pady=5)