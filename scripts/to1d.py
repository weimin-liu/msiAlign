import os
import re
import sqlite3
from tkinter import messagebox

import numpy as np
import pandas as pd

from scripts.parser import extract_mzs, extract_special


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

        # Combine dataframes
        coords_df = pd.concat([spot_names_df, xray_array_df, linescan_array_df], axis=1)
        df = pd.merge(coords_df, df, on='spot_name')
        return df

    finally:
        db_handler.close()


def get_chunks(depth, horizon_size, min_n_samples=10):
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
        start_index = current_index

    return chunks


def to_1d(df, chunks, how: str):
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
        else:
            # Evaluate custom expression
            try:
                safe_dict = {'data': data}
                v = eval(how, {"__builtins__": None}, safe_dict)
                df_1d_list.append(v)
            except Exception as e:
                print(f"Error evaluating custom expression '{how}': {e}")
                return pd.DataFrame()

    df_1d = pd.DataFrame(df_1d_list)
    return df_1d


def get_depth_profile_from_gui(exported_txt_paths, sqlite_db_path, target_cmpds_str, how_str, tol, min_snr, min_int,
                               min_n_samples, horizon_size, save_path, save_path_1d):
    """
    Processes exported txt files to create depth profiles, using parameters provided from GUI.
    Saves the resulting data to specified paths.
    """
    # Convert parameters to appropriate types
    tol = float(tol) if tol is not None else None
    min_snr = float(min_snr) if min_snr is not None else None
    min_int = float(min_int) if min_int is not None else None
    min_n_samples = int(min_n_samples) if min_n_samples is not None else None
    horizon_size = float(horizon_size) / 10000 if horizon_size is not None else None  # Convert μm to cm

    # Parse target compounds
    if target_cmpds_str:
        target_cmpds = dict([cmpd.split(':') for cmpd in target_cmpds_str.strip(';').split(';')])
        target_cmpds = {name: float(mz) for name, mz in target_cmpds.items()}
    else:
        # Parse target compounds from 'how_str'
        target_cmpds = {}
        how_list = how_str.split(';')
        for cmpd in how_list:
            elements = re.findall(r'\b\w+\b', cmpd)
            for elem in elements:
                target_cmpds[elem] = None

    # Process each exported txt path
    exported_txt_paths = [path for path in exported_txt_paths.strip(';').split(';') if path]
    df_1d_list = []

    for idx, path in enumerate(exported_txt_paths):
        if os.path.exists(path):
            if tol is None and min_snr is None and min_int is None:
                df = pd.read_csv(path)
            else:
                df = get_mz_int_depth(path, sqlite_db_path, target_cmpds, tol=tol, min_snr=min_snr,
                                      min_int=min_int)
                # Save the dataframe
                _save_path = save_path.replace('.csv', f'_{idx}.csv') if len(exported_txt_paths) > 1 else save_path
                df.to_csv(_save_path, index=False)

            df = df.dropna()
            df = df.sort_values(by='d')

            # Get chunks and depth
            chunks = get_chunks(df['d'], horizon_size, min_n_samples=min_n_samples)
            depth_1d = to_1d(df, chunks, "data['d'].mean()")

            # Process 'how_str'
            how_list = how_str.split(';')
            ratio_1d_list = []
            for r_how in how_list:
                expr = r_how
                for element in target_cmpds.keys():
                    expr = expr.replace(element, f"data['{element}']")
                ratio_1d = to_1d(df, chunks, expr)
                ratio_1d_list.append(ratio_1d)

            # Combine results
            ratio_1d_df = pd.concat(ratio_1d_list, axis=1)
            ratio_1d_df.columns = how_list
            horizon_counts = [chunk[1] - chunk[0] for chunk in chunks]

            df_1d = pd.DataFrame({
                'd': depth_1d['d'],
                'horizon_count': horizon_counts,
                'slide': [os.path.basename(path)] * len(depth_1d)
            })
            df_1d = pd.concat([df_1d, ratio_1d_df], axis=1)

            # Save 1D depth profile
            _save_path_1d = save_path_1d.replace('.csv', f'_{idx}.csv') if len(exported_txt_paths) > 1 else save_path_1d
            df_1d.to_csv(_save_path_1d, index=False)
            df_1d_list.append(df_1d)

    # Concatenate all 1D depth profiles if multiple files
    if len(df_1d_list) > 1:
        all_df_1d = pd.concat(df_1d_list, axis=0, ignore_index=True)
        all_df_1d.to_csv(save_path_1d.replace('.csv', '_all.csv'), index=False)

    messagebox.showinfo("Done", "The downcore profile has been successfully created")


if __name__ == "__main__":
    pass