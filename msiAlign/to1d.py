import os
import re
import sqlite3
from tkinter import messagebox

import numpy as np
import pandas as pd

from msiAlign.parser import extract_mzs, extract_special


class DatabaseHandler:
    """Handles database interactions for the application."""

    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)

    def close(self):
        """Closes the database connection."""
        self.conn.close()

    def get_spec_id_by_spec_file_name(self, spec_file_name):
        """Retrieves spec_id for a given spec_file_name."""
        query = 'SELECT spec_id FROM metadata WHERE spec_file_name = ?'
        return self.conn.execute(query, (spec_file_name,)).fetchall()

    def get_spec_file_name_by_export_da_name(self, export_da_name):
        """Retrieves spec_file_name for a given export_da_name."""
        query = 'SELECT spec_file_name FROM metadata WHERE export_da_name = ?'
        return self.conn.execute(query, (export_da_name,)).fetchall()

    def ensure_column_exists(self, table_name, column_name, column_type):
        """Ensures a column exists in a table; adds it if not."""
        cursor = self.conn.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        if column_name not in columns:
            self.conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            self.conn.commit()

    def update_export_da_name(self, spec_file_name, export_da_name):
        """Updates the export_da_name for a given spec_file_name."""
        self.ensure_column_exists('metadata', 'export_da_name', 'TEXT')
        self.conn.execute('''
            UPDATE metadata
            SET export_da_name = ?
            WHERE spec_file_name = ?
        ''', (export_da_name, spec_file_name))
        self.conn.commit()

    def create_dataview(self):
        """Creates a view in the database for data retrieval."""
        self.conn.execute('''
            CREATE VIEW IF NOT EXISTS dataview AS
            SELECT metadata.spec_id, metadata.spec_file_name, metadata.spot_name,
                   transformation.xray_array, transformation.linescan_array
            FROM metadata
            INNER JOIN transformation ON metadata.spec_id = transformation.spec_id
        ''')

    def get_coords_by_spec_file_name(self, spec_file_name):
        """Retrieves coordinates data for a given spec_file_name."""
        query = '''
            SELECT spot_name, xray_array, linescan_array
            FROM dataview
            WHERE spec_file_name = ?
        '''
        return self.conn.execute(query, (spec_file_name,)).fetchall()

    def get_grayscale_color_by_spec_file_name(self, spec_file_name):
        query = '''
            SELECT color_values
            FROM metadata
            WHERE spec_file_name = ?
        '''
        try:
            return self.conn.execute(query, (spec_file_name,)).fetchall()
        except sqlite3.OperationalError:
            return None

    def get_tic_by_spec_file_name(self, spec_file_name):
        """Retrieves TIC data for a given spec_file_name."""
        query = '''
            SELECT TIC
            FROM metadata
            WHERE spec_file_name = ?
        '''
        try:
            return self.conn.execute(query, (spec_file_name,)).fetchall()
        except sqlite3.OperationalError:
            return None

def get_spec_file_name_from_txt(DA_txt_path):
    """Parses the spectrum file name from the txt file path."""
    return os.path.basename(DA_txt_path).replace('.txt', '')


def ensure_first_last_spotnumber_columns(db_handler):
    """
    Ensures that 'first_spot_number' and 'last_spot_number' columns exist in 'metadata'.
    Adds and populates them based on 'spot_name' if they don't.
    """
    cursor = db_handler.conn.execute("PRAGMA table_info(metadata)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'first_spot_number' not in columns or 'last_spot_number' not in columns:
        if 'first_spot_number' not in columns:
            db_handler.conn.execute("ALTER TABLE metadata ADD COLUMN first_spot_number TEXT")
        if 'last_spot_number' not in columns:
            db_handler.conn.execute("ALTER TABLE metadata ADD COLUMN last_spot_number TEXT")
        db_handler.conn.commit()

        cursor = db_handler.conn.execute("SELECT spec_id, spot_name FROM metadata")
        metadata = cursor.fetchall()
        metadata_df = pd.DataFrame(metadata, columns=['spec_id', 'spot_name'])
        metadata_df['spot_list'] = metadata_df['spot_name'].str.split(',')
        metadata_df['first_spot_number'] = metadata_df['spot_list'].apply(
            lambda lst: re.findall(r'R\d+X\d+Y\d+', lst[0])[0] if lst else None)
        metadata_df['last_spot_number'] = metadata_df['spot_list'].apply(
            lambda lst: re.findall(r'R\d+X\d+Y\d+', lst[-1])[0] if lst else None)

        for _, row in metadata_df.iterrows():
            db_handler.conn.execute('''
                UPDATE metadata
                SET first_spot_number = ?, last_spot_number = ?
                WHERE spec_id = ?
            ''', (row['first_spot_number'], row['last_spot_number'], row['spec_id']))
        db_handler.conn.commit()


def extract_first_last_spotnumber(txt_path):
    """Extracts the first and last spot numbers from the txt file."""
    with open(txt_path, 'r') as f:
        lines = f.readlines()
        # Extract first spot number
        for line in lines:
            match = re.match(r'R\d+X\d+Y\d+', line)
            if match:
                first_spot_number = match.group(0)
                break
        # Extract last spot number
        for line in reversed(lines):
            match = re.match(r'R\d+X\d+Y\d+', line)
            if match:
                last_spot_number = match.group(0)
                break
    return first_spot_number, last_spot_number


def pair_txt_spec_on_first_last_spotnumber(db_handler, txt_path):
    """
    Pairs the txt file with a spectrum file name based on first and last spot numbers.
    Returns the spec_file_name if found; otherwise, None.
    """
    ensure_first_last_spotnumber_columns(db_handler)
    first_spot_number, last_spot_number = extract_first_last_spotnumber(txt_path)
    cursor = db_handler.conn.execute('''
        SELECT spec_file_name FROM metadata
        WHERE first_spot_number = ? AND last_spot_number = ?
    ''', (first_spot_number, last_spot_number))
    spec_name = cursor.fetchall()
    return spec_name[0][0] if spec_name else None


def find_spec_file_name(db_handler, DA_txt_path):
    """
    Attempts to find the spec_file_name associated with a DA_txt_path.
    Tries multiple methods and prompts the user if necessary.
    """
    spec_file_name = get_spec_file_name_from_txt(DA_txt_path)

    # Check if spec_file_name exists in the database
    if db_handler.get_spec_id_by_spec_file_name(spec_file_name):
        return spec_file_name

    # Try pairing based on first and last spot numbers
    spec_file_name = pair_txt_spec_on_first_last_spotnumber(db_handler, DA_txt_path)
    if spec_file_name:
        return spec_file_name

    # Try finding based on export_da_name
    export_da_name = os.path.basename(DA_txt_path)
    result = db_handler.get_spec_file_name_by_export_da_name(export_da_name)
    if len(result) == 1:
        return result[0][0]

    # Prompt user for spec_file_name
    if messagebox.askyesno("Error", "The spectrum file name does not exist in the database. "
                                    "Do you want to manually type the spectrum file name?"):
        while True:
            spec_file_name = input("Please enter the spectrum file name: ")
            result = db_handler.get_spec_id_by_spec_file_name(spec_file_name)
            if len(result) == 1:
                db_handler.update_export_da_name(spec_file_name, export_da_name)
                return spec_file_name
            else:
                messagebox.showerror("Error", "The spectrum file name does not exist in the database or is not unique")
    else:
        return None


def get_mz_int_depth(DA_txt_path, db_path, target_cmpds=None, tol=0.01, min_snr=1, min_int=10000,
                     normalization=False) -> pd.DataFrame:
    """
    Extracts m/z intensities and depth information from a DA exported text file,
    combining it with metadata from the database.
    """
    db_handler = DatabaseHandler(db_path)
    try:
        spec_file_name = find_spec_file_name(db_handler, DA_txt_path)
        if spec_file_name is None:
            messagebox.showerror("Error", "The spectrum file name could not be determined.")
            return pd.DataFrame()

        # Extract target compounds from the DA_txt_path
        if target_cmpds is None:
            df = extract_special(DA_txt_path, mz_range='full', min_snr=min_snr)
        else:
            df = extract_mzs(target_cmpds, DA_txt_path, tol=tol, min_snr=min_snr,
                             min_int=min_int, normalization=normalization)

        # Create data view and retrieve coordinates
        db_handler.create_dataview()
        coords_result = db_handler.get_coords_by_spec_file_name(spec_file_name)
        coords_result_color = db_handler.get_grayscale_color_by_spec_file_name(spec_file_name)
        coords_result_tic = db_handler.get_tic_by_spec_file_name(spec_file_name)

        if not coords_result:
            messagebox.showerror("Error", "The spectrum file name does not exist in the database. "
                                          "Ensure the DA export file name matches the spectrum file name in the database.")
            return pd.DataFrame()

        coords = coords_result[0]
        spot_names = [re.findall(r'R\d+X\d+Y\d+', name)[0] for name in coords[0].split(',')]
        spot_names_df = pd.DataFrame(spot_names, columns=['spot_name'])

        xray_array = np.frombuffer(coords[1], dtype=np.float64).reshape(-1, 2)
        xray_array_df = pd.DataFrame(xray_array, columns=['px', 'py'])

        linescan_array = np.frombuffer(coords[2], dtype=np.float64).reshape(-1, 2)
        linescan_array_df = pd.DataFrame(linescan_array[:, 0], columns=['d'])

        if coords_result_color:
            try:
                color_values = np.frombuffer(coords_result_color[0][0], dtype=np.uint8)
                color_values = color_values.reshape(-1, 1)
                color_values_df = pd.DataFrame(color_values, columns=['color_values'])
            except TypeError:
                color_values_df = pd.DataFrame(np.nan, index=np.arange(len(spot_names)), columns=['color_values'])
        else:
            color_values_df = pd.DataFrame(np.nan, index=np.arange(len(spot_names)), columns=['color_values'])

        if coords_result_tic:
            try:
                coords_result_tic = coords_result_tic[0][0]
                coords_result_tic = eval(coords_result_tic)
                tic_df = pd.DataFrame(coords_result_tic, columns=['TIC'])
                tic_df = tic_df.astype({'TIC': float})
            except TypeError:
                tic_df = pd.DataFrame(np.nan, index=np.arange(len(spot_names)), columns=['TIC'])
        else:
            tic_df = pd.DataFrame(np.nan, index=np.arange(len(spot_names)), columns=['TIC'])

        # Combine dataframes
        coords_df = pd.concat([spot_names_df, xray_array_df, linescan_array_df,color_values_df, tic_df], axis=1)
        df = pd.merge(coords_df, df, on='spot_name')

        if normalization == "TIC" or normalization == "tic":
            # normalization all 'int_' columns by TIC
            int_cols = [col for col in df.columns if col.startswith('int_')]
            df[int_cols] = df[int_cols].div(df['TIC'], axis=0)

        return df

    finally:
        db_handler.close()


def get_chunks(depth, horizon_size, min_n_samples=10,dynamic=False,res=200,max_extra_row=5):
    """
    Divides the depth array into chunks based on horizon size and minimum number of samples.
    Returns a list of (start_index, end_index) tuples representing chunks.
    """
    depth = np.array(depth)
    if not np.all(np.diff(depth) >= 0):
        raise ValueError("The depth array is not sorted")

    start_index = 0
    chunks = []
    n = len(depth)

    while start_index < n:
        end_value = depth[start_index] + horizon_size
        current_index = start_index
        while current_index < n and depth[current_index] <= end_value:
            current_index += 1
        if current_index - start_index >= min_n_samples:
            chunks.append((start_index, current_index))
        else:
            # if the chunk is too small, depend on dynamic to decide if we should add more rows
            if dynamic:
                # if the chunk is too small, add more rows until the chunk is larger than min_n_samples
                retry = 0
                while current_index - start_index < min_n_samples and current_index < n and retry < max_extra_row:
                    end_value = depth[current_index] + res
                    retry += 1
                    while current_index < n and depth[current_index] <= end_value:
                        current_index += 1
                if current_index - start_index >= min_n_samples:
                    chunks.append((start_index, current_index))
            else:
                # if the chunk is too small, ignore it
                pass

        start_index = current_index


    return chunks


def to_1d(df, chunks, how: str) -> pd.DataFrame:
    """
    Aggregates data in df over the given chunks using the specified method.
    Returns a DataFrame of aggregated values for each chunk.
    """
    int_cols = [col for col in df.columns if 'int' in col or 'tic' in col
                or 'median' in col or 'weight_mz' in col]
    df_1d_list = []

    for chunk in chunks:
        start_index, end_index = chunk
        data = df.iloc[start_index:end_index]
        int_data = data[int_cols]
        valid_counts = int_data.count()
        valid_mask = valid_counts >= 10

        if how == 'mean':
            v = int_data.mean()
            v[~valid_mask] = 0
            df_1d_list.append(v)
        elif how == 'std':
            v = int_data.std()
            v[~valid_mask] = 0
            df_1d_list.append(v)
        elif how == 'sum':
            v = int_data.sum()
            v[~valid_mask] = 0
            df_1d_list.append(v)
        elif how == 'median':
            v = int_data.median()
            v[~valid_mask] = 0
            df_1d_list.append(v)
        elif how == 'sumall':
            v = int_data.sum().sum()
            df_1d_list.append(v)

        else:
            # Evaluate custom expression
            try:
                safe_dict = {'data': data}
                v = eval(how, {"__builtins__": None}, safe_dict)
                df_1d_list.append(v)
            except Exception as e:
                messagebox.showerror(title="Error", message=f"Error evaluating expression: {e}")
                return pd.DataFrame()

    df_1d = pd.DataFrame(df_1d_list)
    return df_1d



def get_msi_depth_profile_from_gui(exported_txt_path, sqlite_db_path, target_cmpds, how, spot_method,dynamic,dyn_res,dyn_max_retry, tol, min_snr, min_int,
                               min_n_samples,
                               horizon_size, save_path, save_path_1d, additional_params,
                                   **kwargs):
    # conver all values to float
    tol = float(tol)
    min_snr = float(min_snr)
    min_int = float(min_int)
    min_n_samples = int(min_n_samples)
    spot_method = spot_method
    dynamic = bool(dynamic)
    dyn_res = float(dyn_res) / 10000  # convert to cm
    dyn_max_retry = int(dyn_max_retry)

    additional_params = additional_params
    additional_params = {param.split(':')[0]: param.split(':')[1] for param in additional_params.split(';') if param.strip() != ''}

    if 'normalization' in additional_params:
        normalization = additional_params['normalization']
    else:
        normalization = False

    horizon_size = float(horizon_size) / 10000  # convert to cm
    # convert target_cmpds string "name1:mz1;name2:mz2" to a dictionary
    # handle possible trailing semicolons gracefully
    cmpd_pairs = [c for c in target_cmpds.split(';') if c.strip()]
    target_cmpds = dict(pair.split(':') for pair in cmpd_pairs)
    # make sure the values are floats
    target_cmpds = {name: float(mz) for name, mz in target_cmpds.items()}
    # get exported_txt_path, seperated by ';' and trim the last ';' if there is one
    exported_txt_path = exported_txt_path.split(';')
    if exported_txt_path[-1] == '':
        exported_txt_path = exported_txt_path[:-1]
    # find the first existing path
    df_1d_list = []
    for path in exported_txt_path:
        if os.path.exists(path):
            single_exported_txt_path = path
            df = get_mz_int_depth(single_exported_txt_path, sqlite_db_path, target_cmpds, tol=tol, min_snr=min_snr,
                                  min_int=min_int, normalization=normalization)
            df = df.sort_values(by='d')

            # save the dataframe
            # append save_path with index if there are multiple exported_txt_path
            if len(exported_txt_path) > 1:
                _save_path = save_path.replace('.csv', f'_{exported_txt_path.index(single_exported_txt_path)}.csv')
            else:
                _save_path = save_path
            df.to_csv(_save_path, index=False)

            # this part record the missing depth for correct plotting
            if not dynamic:
                fake_chunks = get_chunks(df['d'], horizon_size, min_n_samples=0)
                fake_depth_1d = to_1d(df, fake_chunks, "data['d'].mean()")
                fake_depth_1d.columns = ['d']

            # replace the 0s in the int columns with np.nan
            int_cols = [col for col in df.columns if 'int' in col ]
            df[int_cols] = df[int_cols].replace(0, np.nan)
            if spot_method == 'all':
                # in all mode, drop the int columns where any of the compounds is zero
                df = df.dropna(subset=int_cols, how='any')
            elif spot_method == 'any':
                # in any mode, drop the int columns where all the compounds are zero
                df = df.dropna(subset=int_cols, how='all')
            else:
                # in custom mode, drop the column by spot_method
                custom_cmpd_list = [s for s in spot_method.split(';') if s.strip()]
                custom_cmpd_list = ['int_'+custom_cmpd for custom_cmpd in custom_cmpd_list]
                df = df.dropna(subset=custom_cmpd_list, how='any')
            # fill the nan with 0
            df[int_cols] = df[int_cols].fillna(0)
            df = df.sort_values(by='d')

            chunks = get_chunks(df['d'], horizon_size, min_n_samples=min_n_samples,dynamic=dynamic,res=dyn_res,max_extra_row=dyn_max_retry)
            if len(chunks) == 0:
                df_1d = pd.DataFrame(columns=['d (cm)', 'horizon_count','horizon_len (cm)', 'slide', 'result'])
            else:
                # get the mean depth of each chunk
                depth_1d = to_1d(df, chunks, "data['d'].mean()")
                depth_1d_min = to_1d(df, chunks, "data['d'].min()")
                depth_1d_max = to_1d(df, chunks, "data['d'].max()")
                depth_1d_size = depth_1d_max - depth_1d_min
                ratio_1d = to_1d(df, chunks, how)
                horizon_count = [chunk[1] - chunk[0] for chunk in chunks]
                df_1d = pd.DataFrame({'d (cm)': depth_1d.iloc[:, 0],
                                      'horizon_count': horizon_count,
                                      'horizon_len (cm)': depth_1d_size.iloc[:, 0],
                                      'slide': [os.path.basename(single_exported_txt_path)] * len(depth_1d),
                                      'result': ratio_1d.iloc[:, 0]})

                try:
                    if not dynamic:
                        # add the missing depth to the result
                        # for each of the depth in fake_depth_1d, if it is not in df_1d +- horizon_size, add it to df_1d
                        for idx, row in fake_depth_1d.iterrows():
                            if not ((row['d'] - horizon_size < df_1d['d (cm)']) & (df_1d['d (cm)'] < row['d'] + horizon_size)).any():
                                df_1d = pd.concat(
                                    [df_1d,
                                     pd.DataFrame(
                                         {'d (cm)': [row['d']],
                                          'horizon_count': np.nan,
                                          'horizon_len (cm)': np.nan,
                                          'slide': [os.path.basename(single_exported_txt_path)],
                                          'result': np.nan})],
                                    axis=0, ignore_index=True)
                # if anything goes wrong, just pass, as it is not critical when the missing depth is not added
                except Exception as e:
                    print(e)
                    pass

            df_1d = df_1d.sort_values(by='d (cm)')

            # save the 1d depth profile
            if len(exported_txt_path) > 1:
                _save_path_1d = save_path_1d.replace('.csv',
                                                     f'_{exported_txt_path.index(single_exported_txt_path)}.csv')
            else:
                _save_path_1d = save_path_1d
            df_1d.to_csv(_save_path_1d, index=False)
            df_1d_list.append(df_1d)

    # Concatenate all 1D depth profiles if multiple files
    if len(df_1d_list) > 1:
        all_df_1d = pd.concat(df_1d_list, axis=0, ignore_index=True)
        all_df_1d.to_csv(save_path_1d.replace('.csv', '_all.csv'), index=False)
    else:
        all_df_1d = df_1d_list[0]

    show_tk_message = kwargs.get('show_tk_message', True)
    if show_tk_message:
        # create a tkinter messagebox to show the user it's done and add an ok button to close the window
        messagebox.showinfo(title="Done", message="The downcore profile has been successfully created")

    return_df_1d = kwargs.get('return_df_1d', False)
    if return_df_1d:
        return all_df_1d


def get_xrf_depth_profile_from_gui(exported_csv_path, how,
                               min_n_samples,
                               horizon_size, save_path_1d):
    # conver all values to float
    min_n_samples = int(min_n_samples)
    horizon_size = float(horizon_size) / 10000 # convert to cm
    # parse all the target elements from how: Al/Ca, Ca/Ti, etc., ignoring trailing semicolons
    how = [h for h in how.split(';') if h.strip()]
    # get exported_csv_path, seperated by ';' and trim the last ';' if there is one
    exported_csv_path = exported_csv_path.split(';')
    if exported_csv_path[-1] == '':
        exported_csv_path = exported_csv_path[:-1]
    df_list = []
    # find the first existing path
    for path in exported_csv_path:
        if os.path.exists(path):
            single_exported_csv_path = path
            df = pd.read_csv(single_exported_csv_path)
            df = df.dropna()
            # use the mask
            try:
                df = df[df['mask']]
            except Exception as e:
                print(e)
                return
            try:
                df = df.sort_values(by='d')
            except KeyError:
                messagebox.showerror("Error", "The exported csv file does not contain a 'd' column.")
                return
            chunks = get_chunks(df['d'], horizon_size, min_n_samples=min_n_samples)
            # get the mean depth of each chunk
            depth_1d = to_1d(df, chunks, "data['d'].mean()")
            ratio_1ds = []
            for r_how in how:
                if '/' in r_how:
                    e0 = r_how.split('/')[0]
                    e1 = r_how.split('/')[1]
                    ratio_1d = to_1d(df, chunks, f"data['{e0}'].sum()/data['{e1}'].sum()")
                    ratio_1ds.append(ratio_1d)
                else:
                    ratio_1d = to_1d(df, chunks, f"data['{r_how}'].mean()")
                    ratio_1ds.append(ratio_1d)
            horizon_count = [chunk[1] - chunk[0] for chunk in chunks]
            df_1d = pd.DataFrame({'d': depth_1d.iloc[:, 0],
                                    'horizon_count': horizon_count})
            for idx, ratio_1d in enumerate(ratio_1ds):
                df_1d[f'{how[idx]}'] = ratio_1d.iloc[:, 0]

            # save the 1d depth profile
            if len(exported_csv_path) > 1:
                _save_path_1d = save_path_1d.replace('.csv',
                                                     f'_{exported_csv_path.index(single_exported_csv_path)}.csv')
            else:
                _save_path_1d = save_path_1d
            df_1d.to_csv(_save_path_1d, index=False)
            df_list.append(df_1d)

    if len(df_list) > 1:
        all_df_1d = pd.concat(df_list, axis=0, ignore_index=True)
        all_df_1d.to_csv(save_path_1d.replace('.csv', '_all.csv'), index=False)

    # create a tkinter messagebox to show the user it's done and add an ok button to close the window
    messagebox.showinfo("Done", "The downcore profile has been successfully created")


if __name__ == "__main__":
    pass