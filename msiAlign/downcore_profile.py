import tkinter as tk
from tkinter import filedialog
from tkinter.ttk import Combobox

from msiAlign.to1d import get_msi_depth_profile_from_gui, get_xrf_depth_profile_from_gui


def validate_input(target_cmpds, spot_method):
    """
    Validate the input
    :param target_cmpds: target compounds
    :param spot_method: method to combine spots
    :return:
    """
    if spot_method.lower() == 'all' or spot_method.lower() == 'any':
        return True
    else:
        cmpds = target_cmpds.split(';')
        cmpds = [c.split(':')[0] for c in cmpds]
        spot_method = spot_method.split(';')
        for s in spot_method:
            if s not in cmpds:
                return False
        return True


def calc_depth_profile_combined():
    """Calculate the depth profile (combined mode)"""
    window = tk.Toplevel()
    window.title("Calc Downcore Profile")
    widgets = {}
    row_index = 0

    # Mode selector
    tk.Label(window, text="Mode:").grid(row=row_index, column=0, sticky='nsew')
    mode_selector = Combobox(window, values=['MSI', 'XRF'])
    mode_selector.current(0)
    mode_selector.grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    # MSI mode widgets
    widgets['exported_txt_label'] = tk.Label(window, text="Exported txt path(s):")
    widgets['exported_txt_entry'] = tk.Entry(window)
    widgets['exported_txt_button'] = tk.Button(window, text="Select", command=lambda: widgets['exported_txt_entry'].insert(
        tk.END,
        ';'.join(filedialog.askopenfilenames(title='Select exported txt', filetypes=[("Plain text files", "*.txt")])) + ';'
    ))

    widgets['exported_txt_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['exported_txt_entry'].grid(row=row_index, column=1, sticky='nsew')
    widgets['exported_txt_button'].grid(row=row_index, column=2, sticky='nsew')
    row_index += 1

    widgets['sqlite_db_label'] = tk.Label(window, text="Sqlite db path:")
    widgets['sqlite_db_entry'] = tk.Entry(window)
    widgets['sqlite_db_button'] = tk.Button(window, text="Select", command=lambda: widgets['sqlite_db_entry'].insert(
        tk.END,
        filedialog.askopenfilename(title='Select sqlite db', filetypes=[("SQLite files", "*.db")])
    ))

    widgets['sqlite_db_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['sqlite_db_entry'].grid(row=row_index, column=1, sticky='nsew')
    widgets['sqlite_db_button'].grid(row=row_index, column=2, sticky='nsew')
    row_index += 1

    widgets['target_cmpds_label'] = tk.Label(window, text="Target cmpds:")
    widgets['target_cmpds_combo'] = Combobox(window, values=(
        "name1:mz1;name2:mz2",
        "GDGT0:1324.3046;GDGT5:1314.2264",
        "ALK37_2:553.5319;ALK37_3:551.5162"
    ))
    widgets['target_cmpds_combo'].current(0)

    widgets['target_cmpds_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['target_cmpds_combo'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    widgets['how_label'] = tk.Label(window, text="How:")
    widgets['how_entry'] = Combobox(window, values=(
        "data['int_name1'].sum() / (data['int_name1'].sum() + data['int_name2'].sum())",
        "sumall"
    ))
    widgets['how_entry'].current(0)

    widgets['how_button'] = tk.Button(window, text="Generate", command=lambda: [
        widgets['how_entry'].delete(0, tk.END),
        widgets['how_entry'].insert(
            tk.END,
            f"data['int_{widgets['target_cmpds_combo'].get().split(';')[0].split(':')[0]}'].sum() / "
            f"(data['int_{widgets['target_cmpds_combo'].get().split(';')[0].split(':')[0]}'].sum() +"
            f"data['int_{widgets['target_cmpds_combo'].get().split(';')[1].split(':')[0]}'].sum())"
        )
    ])


    widgets['how_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['how_entry'].grid(row=row_index, column=1, sticky='nsew')
    widgets['how_button'].grid(row=row_index, column=2, sticky='nsew')
    row_index += 1

    widgets['method_label'] = tk.Label(window, text="Spot method:")
    widgets['method_entry'] = Combobox(window, values=(
        "all",
        "any",
        "other:type in the cmpds, sep by ';'"))
    widgets['method_entry'].current(0)
    widgets['method_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['method_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    widgets['method_dynamic_label'] = tk.Label(window, text="Dynamic spots:")
    # add a checkbox to enable dynamic spots or not
    widgets['method_dynamic_var'] = tk.IntVar()
    widgets['method_dynamic_checkbox'] = tk.Checkbutton(window, variable=widgets['method_dynamic_var'])
    widgets['method_dynamic_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['method_dynamic_checkbox'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    # add dynamic spots parameters
    widgets['dyn_res_label'] = tk.Label(window, text="MSI res (μm):")
    widgets['dyn_res_entry'] = tk.Entry(window)
    widgets['dyn_res_entry'].insert(tk.END, "Only for dynamic spots, default is 200")
    widgets['dyn_res_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['dyn_res_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    widgets['dyn_max_retry'] = tk.Label(window, text="Max extra rows:")
    widgets['dyn_max_retry_entry'] = tk.Entry(window)
    widgets['dyn_max_retry_entry'].insert(tk.END, "Only for dynamic spots, default is 5")
    widgets['dyn_max_retry'].grid(row=row_index, column=0, sticky='nsew')
    widgets['dyn_max_retry_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1


    widgets['tol_label'] = tk.Label(window, text="Tol (Da, full window):")
    widgets['tol_entry'] = tk.Entry(window)
    widgets['tol_entry'].insert(tk.END, "0.01")

    widgets['tol_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['tol_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    widgets['min_snr_label'] = tk.Label(window, text="Min snr:")
    widgets['min_snr_entry'] = tk.Entry(window)
    widgets['min_snr_entry'].insert(tk.END, "1")

    widgets['min_snr_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['min_snr_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    widgets['min_int_label'] = tk.Label(window, text="Min int:")
    widgets['min_int_entry'] = tk.Entry(window)
    widgets['min_int_entry'].insert(tk.END, "10000")

    widgets['min_int_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['min_int_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    widgets['save_2d_label'] = tk.Label(window, text="Save 2D to:")
    widgets['save_2d_entry'] = tk.Entry(window)
    widgets['save_2d_entry'].insert(tk.END, "2D_res.csv")
    widgets['save_2d_button'] = tk.Button(window, text="Select", command=lambda: [
        widgets['save_2d_entry'].delete(0, tk.END),
        widgets['save_2d_entry'].insert(
            tk.END,
            filedialog.asksaveasfilename(title="Save 2d result as",
                                         defaultextension=".csv",
                                         filetypes=[("CSV file", '*.csv')])
        )
    ])

    widgets['save_2d_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['save_2d_entry'].grid(row=row_index, column=1, sticky='nsew')
    widgets['save_2d_button'].grid(row=row_index, column=2, sticky='nsew')
    row_index += 1

    # XRF mode widgets
    widgets['transformed_csv_label'] = tk.Label(window, text="Transformed csv path(s):")
    widgets['transformed_csv_entry'] = tk.Entry(window)
    widgets['transformed_csv_button'] = tk.Button(window, text="Select", command=lambda: widgets['transformed_csv_entry'].insert(
        tk.END,
        ';'.join(filedialog.askopenfilenames(title='Select transformed csv', filetypes=[("CSV files", "*.csv")])) + ';'
    ))

    widgets['transformed_csv_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['transformed_csv_entry'].grid(row=row_index, column=1, sticky='nsew')
    widgets['transformed_csv_button'].grid(row=row_index, column=2, sticky='nsew')
    row_index += 1

    widgets['ratios_label'] = tk.Label(window, text="Ratios (sep by ';'):")
    widgets['ratios_entry'] = tk.Entry(window)
    widgets['ratios_entry'].insert(tk.END, "Ca/Ti;Fe/Ti")

    widgets['ratios_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['ratios_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    # Common widgets
    widgets['min_n_samples_label'] = tk.Label(window, text="Min-n-spots/horizon:")
    widgets['min_n_samples_entry'] = tk.Entry(window)
    widgets['min_n_samples_entry'].insert(tk.END, "10")

    widgets['min_n_samples_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['min_n_samples_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    widgets['horizon_size_label'] = tk.Label(window, text="Horizon size (μm):")
    widgets['horizon_size_entry'] = tk.Entry(window)
    widgets['horizon_size_entry'].insert(tk.END, "500")

    widgets['horizon_size_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['horizon_size_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    widgets['save_1d_label'] = tk.Label(window, text="Save 1D to:")
    widgets['save_1d_entry'] = tk.Entry(window)
    widgets['save_1d_entry'].insert(tk.END, "1D_res.csv")
    widgets['save_1d_button'] = tk.Button(window, text="Select", command=lambda: [
        widgets['save_1d_entry'].delete(0, tk.END),
        widgets['save_1d_entry'].insert(
            tk.END,
            filedialog.asksaveasfilename(title="Save 1d result as",
                                         defaultextension=".csv",
                                         filetypes=[("CSV file", '*.csv')])
        )
    ])

    widgets['save_1d_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['save_1d_entry'].grid(row=row_index, column=1, sticky='nsew')
    widgets['save_1d_button'].grid(row=row_index, column=2, sticky='nsew')
    row_index += 1

    # add a widget to input additional parameters for the calculation
    widgets['additional_params_label'] = tk.Label(window, text="Additional params:")
    widgets['additional_params_entry'] = tk.Entry(window)
    widgets['additional_params_entry'].insert(tk.END, "normalization:none;")
    widgets['additional_params_label'].grid(row=row_index, column=0, sticky='nsew')
    widgets['additional_params_entry'].grid(row=row_index, column=1, sticky='nsew')
    row_index += 1

    # Start button
    widgets['start_button'] = tk.Button(window, text="Start")
    widgets['start_button'].grid(row=row_index, column=0, columnspan=3, sticky='nsew')

    # Column configurations
    for i in range(3):
        window.grid_columnconfigure(i, weight=1 if i == 1 else 0)

    # Function to update widget visibility based on mode
    def update_widgets():
        mode = mode_selector.get()
        if mode == 'MSI':
            # Show MSI mode widgets
            widgets['exported_txt_label'].grid()
            widgets['exported_txt_entry'].grid()
            widgets['exported_txt_button'].grid()
            widgets['sqlite_db_label'].grid()
            widgets['sqlite_db_entry'].grid()
            widgets['sqlite_db_button'].grid()
            widgets['target_cmpds_label'].grid()
            widgets['target_cmpds_combo'].grid()
            widgets['how_label'].grid()
            widgets['how_entry'].grid()
            widgets['how_button'].grid()
            widgets['method_label'].grid()
            widgets['method_entry'].grid()
            # Dynamic spots
            widgets['method_dynamic_label'].grid()
            widgets['method_dynamic_checkbox'].grid()
            widgets['dyn_res_label'].grid()
            widgets['dyn_res_entry'].grid()
            widgets['dyn_max_retry'].grid()
            widgets['dyn_max_retry_entry'].grid()


            widgets['tol_label'].grid()
            widgets['tol_entry'].grid()
            widgets['min_snr_label'].grid()
            widgets['min_snr_entry'].grid()
            widgets['min_int_label'].grid()
            widgets['min_int_entry'].grid()
            widgets['save_2d_label'].grid()
            widgets['save_2d_entry'].grid()
            widgets['save_2d_button'].grid()
            widgets['additional_params_label'].grid()
            widgets['additional_params_entry'].grid()

            # Hide XRF mode widgets
            widgets['transformed_csv_label'].grid_remove()
            widgets['transformed_csv_entry'].grid_remove()
            widgets['transformed_csv_button'].grid_remove()
            widgets['ratios_label'].grid_remove()
            widgets['ratios_entry'].grid_remove()
        elif mode == 'XRF':
            # Hide MSI mode widgets
            widgets['exported_txt_label'].grid_remove()
            widgets['exported_txt_entry'].grid_remove()
            widgets['exported_txt_button'].grid_remove()
            widgets['sqlite_db_label'].grid_remove()
            widgets['sqlite_db_entry'].grid_remove()
            widgets['sqlite_db_button'].grid_remove()
            widgets['target_cmpds_label'].grid_remove()
            widgets['target_cmpds_combo'].grid_remove()
            widgets['how_label'].grid_remove()
            widgets['how_entry'].grid_remove()
            widgets['how_button'].grid_remove()

            widgets['method_dynamic_label'].grid_remove()
            widgets['method_dynamic_checkbox'].grid_remove()
            widgets['dyn_res_label'].grid_remove()
            widgets['dyn_res_entry'].grid_remove()
            widgets['dyn_max_retry'].grid_remove()
            widgets['dyn_max_retry_entry'].grid_remove()


            widgets['method_label'].grid_remove()
            widgets['method_entry'].grid_remove()
            widgets['tol_label'].grid_remove()
            widgets['tol_entry'].grid_remove()
            widgets['min_snr_label'].grid_remove()
            widgets['min_snr_entry'].grid_remove()
            widgets['min_int_label'].grid_remove()
            widgets['min_int_entry'].grid_remove()
            widgets['save_2d_label'].grid_remove()
            widgets['save_2d_entry'].grid_remove()
            widgets['save_2d_button'].grid_remove()
            widgets['additional_params_label'].grid_remove()
            widgets['additional_params_entry'].grid_remove()

            # Show XRF mode widgets
            widgets['transformed_csv_label'].grid()
            widgets['transformed_csv_entry'].grid()
            widgets['transformed_csv_button'].grid()
            widgets['ratios_label'].grid()
            widgets['ratios_entry'].grid()

    # Function to start the calculation
    def start_calculation():
        mode = mode_selector.get()
        # Common parameters
        min_n_samples = widgets['min_n_samples_entry'].get()
        horizon_size = widgets['horizon_size_entry'].get()
        save_1d_path = widgets['save_1d_entry'].get()
        if mode == 'MSI':
            # Get values from MSI mode widgets
            exported_txt_path = widgets['exported_txt_entry'].get()
            sqlite_db_path = widgets['sqlite_db_entry'].get()
            target_cmpds = widgets['target_cmpds_combo'].get()
            how = widgets['how_entry'].get()
            spot_method = widgets['method_entry'].get()
            additional_params = widgets['additional_params_entry'].get()

            # Dynamic spots
            # if dynamic spots is enabled, get the values as boolean
            dynamic = widgets['method_dynamic_var'].get()
            dynamic = True if dynamic == 1 else False
            if dynamic:
                dyn_res = widgets['dyn_res_entry'].get()
                dyn_max_retry = widgets['dyn_max_retry_entry'].get()
                # try converting to float, if failed, use default values
                try:
                    dyn_res = float(dyn_res)
                except ValueError:
                    dyn_res = 200
                try:
                    dyn_max_retry = int(dyn_max_retry)
                except ValueError:
                    dyn_max_retry = 5
            else:
                dyn_res = 200
                dyn_max_retry = 5

            tol = widgets['tol_entry'].get()
            min_snr = widgets['min_snr_entry'].get()
            min_int = widgets['min_int_entry'].get()
            save_2d_path = widgets['save_2d_entry'].get()

            if not validate_input(
                target_cmpds=target_cmpds,
                spot_method=spot_method,
            ):
                tk.messagebox.showerror("Error", "Invalid input, please make sure the cmpds listed in 'Method' are valid")
                return

            # Call the processing function
            get_msi_depth_profile_from_gui(
                exported_txt_path, sqlite_db_path, target_cmpds, how, spot_method, dynamic, dyn_res, dyn_max_retry, tol, min_snr, min_int,
                min_n_samples, horizon_size, save_2d_path, save_1d_path, additional_params
            )
        else:
            # XRF mode
            exported_txt_path = widgets['transformed_csv_entry'].get()
            how = widgets['ratios_entry'].get()
            get_xrf_depth_profile_from_gui(
                exported_txt_path, how,
                min_n_samples, horizon_size, save_1d_path
            )


    # Bindings and initializations
    mode_selector.bind("<<ComboboxSelected>>", lambda event: update_widgets())
    widgets['start_button'].config(command=start_calculation)
    update_widgets()