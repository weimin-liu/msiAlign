import re
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Combobox

from scripts.to1d import get_depth_profile_from_gui

import tkinter as tk
from tkinter import filedialog
from tkinter.ttk import Combobox
import tkinter as tk
from tkinter import filedialog
from tkinter.ttk import Combobox

def calc_depth_profile():
    """Combined function to calculate the depth profile for MSI and XRF data."""
    # Create a popup window
    window = tk.Toplevel()
    window.title("Calc Depth Profile")
    window.geometry("400x400")

    # Add a selection box to choose between "MSI" and "XRF" modes
    tk.Label(window, text="Mode:").grid(row=0, column=0, sticky='nsew')
    mode_selection = Combobox(window, values=["MSI", "XRF"])
    mode_selection.grid(row=0, column=1, sticky='nsew')
    mode_selection.current(0)  # Default to "MSI"

    # Entry for exported file path, with a selection button
    tk.Label(window, text="Exported File Path(s):").grid(row=1, column=0, sticky='nsew')
    exported_path = tk.Entry(window)
    exported_path.grid(row=1, column=1, sticky='nsew')
    select_file_button = tk.Button(window, text="Select")
    select_file_button.grid(row=1, column=2, sticky='nsew')

    # SQL DB Path and Target Compounds for MSI only
    tk.Label(window, text="SQL DB Path:").grid(row=2, column=0, sticky='nsew')
    sqlite_db_path = tk.Entry(window)
    sqlite_db_path.grid(row=2, column=1, sticky='nsew')
    sqlite_db_button = tk.Button(window, text="Select",
                                 command=lambda: sqlite_db_path.insert(tk.END, filedialog.askopenfilename(
                                     title='Select SQLite DB', filetypes=[("SQLite files", "*.db")]
                                 )))
    sqlite_db_button.grid(row=2, column=2, sticky='nsew')

    tk.Label(window, text="Target Compounds:").grid(row=3, column=0, sticky='nsew')
    target_cmpds = Combobox(window)
    target_cmpds.grid(row=3, column=1, sticky='nsew')
    target_cmpds['values'] = (
        "name1:mz1;name2:mz2",
        "GDGT0:1324.3046;GDGT5:1314.2264",
        "ALK37_2:553.5319;ALK37_3:551.5162"
    )
    target_cmpds.current(0)

    # Entry for How (formula/ratios), which differs between MSI and XRF
    tk.Label(window, text="How:").grid(row=4, column=0, sticky='nsew')
    how_entry = tk.Entry(window)
    how_entry.insert(tk.END, "data['int_name1'].sum() / (data['int_name1'].sum() + data['int_name2'].sum())")
    how_entry.grid(row=4, column=1, sticky='nsew')

    # Additional parameters common to both modes
    tk.Label(window, text="Min-n-spots/horizon:").grid(row=5, column=0, sticky='nsew')
    min_n_samples = tk.Entry(window)
    min_n_samples.insert(tk.END, "10")
    min_n_samples.grid(row=5, column=1, sticky='nsew')

    tk.Label(window, text="Horizon Size (μm):").grid(row=6, column=0, sticky='nsew')
    horizon_size = tk.Entry(window)
    horizon_size.insert(tk.END, "500")
    horizon_size.grid(row=6, column=1, sticky='nsew')

    # Save paths
    tk.Label(window, text="Save 1D to:").grid(row=7, column=0, sticky='nsew')
    save_path_1d = tk.Entry(window)
    save_path_1d.insert(tk.END, "1D_res.csv")
    save_path_1d.grid(row=7, column=1, sticky='nsew')
    tk.Button(window, text="Select",
              command=lambda: save_path_1d.insert(tk.END, filedialog.asksaveasfilename(
                  title="Save 1D result as", filetypes=[("CSV file", '*.csv')]
              ))).grid(row=7, column=2, sticky='nsew')

    # Grid configuration for expanding the entry columns
    for i in range(3):
        window.grid_columnconfigure(i, weight=1 if i == 1 else 0)

    # Function to show/hide elements based on the selected mode
    def update_ui(event=None):
        mode = mode_selection.get()
        if mode == "MSI":
            sqlite_db_path.grid()  # Show SQL DB Path
            sqlite_db_button.grid()
            target_cmpds.grid()  # Show Target Compounds
            select_file_button.config(
                command=lambda: exported_path.insert(tk.END,
                                                     ';'.join(filedialog.askopenfilenames(
                                                         title='Select Text Files',
                                                         filetypes=[("Text files", "*.txt")]
                                                     ))))
            how_entry.delete(0, tk.END)
            how_entry.insert(tk.END, "data['int_name1'].sum() / (data['int_name1'].sum() + data['int_name2'].sum())")
        else:  # XRF mode
            sqlite_db_path.grid_remove()  # Hide SQL DB Path
            sqlite_db_button.grid_remove()
            target_cmpds.grid_remove()  # Hide Target Compounds
            select_file_button.config(
                command=lambda: exported_path.insert(tk.END,
                                                     ';'.join(filedialog.askopenfilenames(
                                                         title='Select CSV Files',
                                                         filetypes=[("CSV files", "*.csv")]
                                                     ))))
            how_entry.delete(0, tk.END)
            how_entry.insert(tk.END, "Ca/Ti;Fe/Ti")  # Example ratio for XRF

    # Bind the mode selection to update the UI
    mode_selection.bind("<<ComboboxSelected>>", update_ui)
    update_ui()  # Initialize UI based on the default selection

    # Function to start calculation based on the selected mode
    def start_calculation():
        mode = mode_selection.get()
        if mode == "MSI":
            get_depth_profile_from_gui(
                exported_path.get(),
                sqlite_db_path.get(),
                target_cmpds.get(),
                how_entry.get(),
                tol="0.01",  # Additional MSI-specific defaults can go here
                min_snr="1",
                min_int="10000",
                min_n_samples=min_n_samples.get(),
                horizon_size=horizon_size.get(),
                save_path="2D_res.csv",
                save_path_1d=save_path_1d.get()
            )
        elif mode == "XRF":
            get_depth_profile_from_gui(
                exported_path.get(),
                sqlite_db_path=None,
                target_cmpds=None,
                how=how_entry.get(),
                tol=None,
                min_snr=None,
                min_int=None,
                min_n_samples=min_n_samples.get(),
                horizon_size=horizon_size.get(),
                save_path=None,
                save_path_1d=save_path_1d.get()
            )

    # Start button to trigger calculation
    tk.Button(window, text="Start", command=start_calculation).grid(row=8, column=0, columnspan=3, sticky='nsew')

    # Stitch 1D button
    tk.Button(window, text="Stitch 1D", command=lambda: stitch_1d()).grid(row=9, column=0, columnspan=3, sticky='nsew')


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
