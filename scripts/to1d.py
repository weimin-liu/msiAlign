import logging
import os.path
import re
import sqlite3
from tkinter import messagebox

import numpy as np
import pandas as pd

from scripts.parser import extract_mzs, extract_special


def get_mz_int_depth(DA_txt_path, db_path, target_cmpds=None, tol=0.01, min_snr=1, min_int=10000,
                     normalization=False) -> pd.DataFrame:
    """"""
    # parse the spectrum file name from the path
    spec_file_name = os.path.basename(DA_txt_path).replace('.txt', '')
    # connect to the sqlite database
    conn = sqlite3.connect(db_path)

    # test if spec_file_name is in the metadata table
    query = f'''
    SELECT spec_id
    FROM metadata
    WHERE spec_file_name = '{spec_file_name}'
    '''

    if not conn.execute(query).fetchall():
        # get the first and last spot number from the txt file
        spec_file_name = pair_txt_spec_on_first_last_spotnumber(db_path, DA_txt_path)
        if spec_file_name is None:
            # try to find the spec_file_name in the metadata table based on the txt file name if 'export_da_name' exists
            query = f'''
            SELECT spec_file_name
            FROM metadata
            WHERE export_da_name = '{os.path.basename(DA_txt_path)}'
            '''
            spec_file_name = conn.execute(query).fetchall()
            if len(spec_file_name) == 1:
                spec_file_name = spec_file_name[0][0]
            else:
                # ask the user if they want to manually type the spectrum file name
                messagebox.askyesno("Error", "The spectrum file name does not exist in the database. Do you want to manually type"
                                             "the spectrum file name?")
                if messagebox.askyesno:
                    while True:
                        spec_file_name = input("Please enter the spectrum file name: ")
                        # test if entry contains 'spec_file_name' in the metadata table
                        query = f'''
                        SELECT spec_id
                        FROM metadata
                        WHERE '{spec_file_name}' in spec_file_name
                        '''
                        # test if the spec_file_name is unique
                        if len(conn.execute(query).fetchall()) == 1:
                            # get the spec_file_name from the query
                            spec_file_name = conn.execute(query).fetchall()[0][0]
                            # write the txt file name to export_da_name in the metadata table for future reference, create a new
                            # column if it does not exist
                            conn.execute("PRAGMA table_info(metadata)")
                            columns = conn.fetchall()
                            columns = [col[1] for col in columns]
                            if 'export_da_name' not in columns:
                                conn.execute("ALTER TABLE metadata ADD COLUMN export_da_name TEXT")
                            conn.execute(f"UPDATE metadata SET export_da_name = '{os.path.basename(DA_txt_path)}' WHERE spec_file_name = '{spec_file_name}'")
                            conn.commit()
                            break
                        else:
                            messagebox.showerror("Error", "The spectrum file name does not exist in the database or is not unique")

        else:
            logging.info(f"The spectrum file name is {spec_file_name} for {DA_txt_path}")

    # extract the target compounds from exported_txt_path
    if target_cmpds is None:
        df = extract_special(DA_txt_path, mz_range='full',min_snr=min_snr)
    else:
        df = extract_mzs(target_cmpds, DA_txt_path, tol=tol, min_snr=min_snr, min_int=min_int, normalization=normalization)

    # create a view using the spec_id from both tables, spec_file_name from table metadata, spot_name from metadata, and
    # xray_array and linescan_array from table transformation
    conn.execute('''
    CREATE VIEW IF NOT EXISTS dataview AS
    SELECT metadata.spec_id, metadata.spec_file_name, metadata.spot_name, transformation.xray_array, transformation.linescan_array
    FROM metadata
    INNER JOIN transformation
    ON metadata.spec_id = transformation.spec_id
    ''')

    # get the spot_name, xray_array, and linescan_array from the view, where spec_file_name is the same as the one from the
    # exported_txt_path
    query = f'''
    SELECT spot_name, xray_array, linescan_array
    FROM dataview
    WHERE spec_file_name = '{spec_file_name}'
    '''
    try:
        coords = conn.execute(query).fetchall()[0]
    except IndexError:
        messagebox.showerror("Error", "The spectrum file name does not exist in the database. It's very likely"
                                      "that the da export file is not correctly named. Make sure the file name is the "
                                      "same as the spectrum file name in the database")
        return
    spot_names = coords[0].split(',')
    # in every spot_names, only preserve string 'R(0-9)+X(0-9)+Y(0-9)+'
    spot_names = [re.findall(r'R\d+X\d+Y\d+', spot_name)[0] for spot_name in spot_names]
    spot_names = pd.DataFrame(spot_names, columns=['spot_name'])
    xray_array = np.frombuffer(coords[1], dtype=np.float64).reshape(-1, 2)
    xray_array = pd.DataFrame(xray_array, columns=['px', 'py'])
    linescan_array = np.frombuffer(coords[2], dtype=np.float64).reshape(-1, 2)
    linescan_array = pd.DataFrame(linescan_array[:, 0], columns=['d'])
    # merge all the dataframes
    coords = pd.concat([spot_names, xray_array, linescan_array], axis=1)
    # joint the coords and df on 'spot_name'
    df = pd.merge(coords, df, on='spot_name')
    # only keep the successful spectrum, where both GDGT_0 and GDGT_5 are present
    # TODO: record this value somewhere other than log
    logging.debug(f"Successful rate: {df.dropna().shape[0] / df.shape[0]:.2f}")
    return df


# get the chunks of the depth array and return the start and end index of each chunk
def get_chunks(depth, horizon_size, min_n_samples=10):
    # ensure the depth is sorted
    depth = np.array(depth)
    assert all(depth[i] <= depth[i + 1] for i in range(len(depth) - 1)), "The depth array is not sorted"
    start_index = 0
    chunks = []
    while start_index < len(depth):
        end_value = depth[start_index] + horizon_size
        current_index = start_index
        while current_index < len(depth) and depth[current_index] <= end_value:
            current_index += 1
        # if the number of samples in the interval is less than min_n_samples, continue to the next interval
        if current_index - start_index >= min_n_samples:
            chunks.append((start_index, current_index))
        start_index = current_index
    return chunks


def to_1d(df, chunks, how:str):
    # get the mean of the intensities in each chunk
    df_1d = []
    for chunk in chunks:
        start_index, end_index = chunk
        data = df.iloc[start_index:end_index]
        int_val = data[[col for col in data.columns if 'int' in col or 'tic' in col or 'median' in col or 'weight_mz' in col]]
        valid_val = int_val.count()
        valid_val = valid_val >= 10
        if how == 'mean':
            v = int_val.mean()
            # replace the values with 0 if there are less than 10 non nan values
            v[~valid_val] = 0
            df_1d.append(v)
        elif how == 'sum':
            v = int_val.sum()
            v[~valid_val] = 0
            df_1d.append(v)
        elif how == 'median':
            v = int_val.median()
            v[~valid_val] = 0
            df_1d.append(v)
        else:
            try:
                # perform the calculation according to how string
                df_1d.append(eval(how))
            except Exception as e:
                logging.error(f"Error: {e}")
                return
    return df_1d



def depth2time(depth, age_model):
    # convert depth to time using the age model
    return np.interp(depth, age_model['depth'], age_model['age'])


def extract_first_last_spotnumber(txt_path):
    """Extract the first and last spot number from the txt file"""
    with open(txt_path, 'r') as f:
        lines = f.readlines()
        # get the first line starting with 'R\d+X\d+Y\d+'
        for line in lines:
            if re.match(r'R\d+X\d+Y\d+', line):
                first_spot_number = re.findall(r'R\d+X\d+Y\d+', line)[0]
                break
        # get the last line starting with 'R\d+X\d+Y\d+'
        for line in lines[::-1]:
            if re.match(r'R\d+X\d+Y\d+', line):
                last_spot_number = re.findall(r'R\d+X\d+Y\d+', line)[0]
                break
    return first_spot_number, last_spot_number


def pair_txt_spec_on_first_last_spotnumber(sqlite_db_path, txt_path):
    """Pair txt files and spectra on first and last spot number"""
    import sqlite3
    # check if there is 'first_spot_number' and 'last_spot_number' column in the metadata table
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(metadata)")
    columns = cursor.fetchall()
    columns = [col[1] for col in columns]
    # if there is no 'first_spot_number' and 'last_spot_number' column in the metadata table, add them as strings
    if 'first_spot_number' not in columns and 'last_spot_number' not in columns:
        cursor.execute("ALTER TABLE metadata ADD COLUMN first_spot_number TEXT")
        cursor.execute("ALTER TABLE metadata ADD COLUMN last_spot_number TEXT")
        # read the metdata table
        cursor.execute("SELECT spec_id, spot_name FROM metadata")
        metadata = cursor.fetchall()
        metadata = pd.DataFrame(metadata, columns=['spec_id', 'spot_name'])
        # only keep the R(\d+)X(\d+)Y(\d+) part
        metadata['first_spot_number'] = metadata['spot_name'].str.split(',').str[0]
        metadata['first_spot_number'] = metadata['first_spot_number'].apply(
            lambda x: re.findall(r'(R\d+X\d+Y\d+)', x)[0] if x else None)
        metadata['last_spot_number'] = metadata['spot_name'].str.split(',').str[-1]
        metadata['last_spot_number'] = metadata['last_spot_number'].apply(
            lambda x: re.findall(r'(R\d+X\d+Y\d+)', x)[0] if x else None)
        # update the metadata table
        for i, row in metadata.iterrows():
            cursor.execute(
                f"UPDATE metadata SET first_spot_number = '{row['first_spot_number']}' WHERE spec_id = {row['spec_id']}")
            cursor.execute(
                f"UPDATE metadata SET last_spot_number = '{row['last_spot_number']}' WHERE spec_id = {row['spec_id']}")
        conn.commit()

    # for each txt file, extract the first and last spot number
    first_spot_number, last_spot_number = extract_first_last_spotnumber(txt_path)
    spec_name = cursor.execute(
        f"SELECT spec_file_name FROM metadata WHERE first_spot_number = '{first_spot_number}' AND last_spot_number = '{last_spot_number}'").fetchall()
    # assert that there is only one spectrum with the same first and last spot number
    assert len(spec_name) == 1, f"There are {len(spec_name)} spectra with the same first and last spot number"
    if spec_name:
        return spec_name[0][0]
    else:
        return None


def get_depth_profile_from_gui(exported_txt_path, sqlite_db_path, target_cmpds, how, tol, min_snr, min_int,
                               min_n_samples,
                               horizon_size, save_path, save_path_1d):
    # conver all values to float
    tol = float(tol)
    min_snr = float(min_snr)
    min_int = float(min_int)
    min_n_samples = int(min_n_samples)
    horizon_size = float(horizon_size) / 10000  # convert to cm

    # convert taget_cmpds to a dictionary, target_cmpds is a string in the format of "name1:mz1;name2:mz2"
    target_cmpds = dict([cmpd.split(':') for cmpd in target_cmpds.split(';')])
    # make sure the values are floats
    target_cmpds = {name: float(mz) for name, mz in target_cmpds.items()}
    # get exported_txt_path, seperated by ';' and trim the last ';' if there is one
    exported_txt_path = exported_txt_path.split(';')
    if exported_txt_path[-1] == '':
        exported_txt_path = exported_txt_path[:-1]
    # find the first existing path
    for path in exported_txt_path:
        if os.path.exists(path):
            single_exported_txt_path = path
            df = get_mz_int_depth(single_exported_txt_path, sqlite_db_path, target_cmpds, tol=tol, min_snr=min_snr,
                                  min_int=min_int)
            # save the dataframe
            # append save_path with index if there are multiple exported_txt_path
            if len(exported_txt_path) > 1:
                _save_path = save_path.replace('.csv', f'_{exported_txt_path.index(single_exported_txt_path)}.csv')
            else:
                _save_path = save_path
            df.to_csv(_save_path, index=False)
            df = df.dropna()
            df = df.sort_values(by='d')

            chunks = get_chunks(df['d'], horizon_size, min_n_samples=min_n_samples)
            # get the mean depth of each chunk
            depth_1d = to_1d(df, chunks, "data['d'].mean()")
            ratio_1d = to_1d(df, chunks, how)
            horizon_count = [chunk[1] - chunk[0] for chunk in chunks]
            df_1d = pd.DataFrame({'d': depth_1d,
                                  'ratio': ratio_1d,
                                  'horizon_count': horizon_count,
                                  'slide': [os.path.basename(single_exported_txt_path)] * len(depth_1d)})
            # save the 1d depth profile
            if len(exported_txt_path) > 1:
                _save_path_1d = save_path_1d.replace('.csv',
                                                     f'_{exported_txt_path.index(single_exported_txt_path)}.csv')
            else:
                _save_path_1d = save_path_1d
            df_1d.to_csv(_save_path_1d, index=False)

    # create a tkinter messagebox to show the user it's done and add an ok button to close the window
    messagebox.showinfo("Done", "The downcore profile has been successfully created")


# The following function is for the command line interface, not used in the GUI
# def get_depth_profile():
#     # if there is a parameters files in the same directory, use the parameters file
#     if os.path.exists('params.py'):
#         params_path = os.getcwd() + '/params.py'
#     else:
#         # ask the user for parameters path
#         params_path = input("Please enter the path to the parameters file: ")
#     # load the parameters
#     import sys
#     sys.path.append(os.path.dirname(params_path))
#     try:
#         from params import target_cmpds, exported_txt_path, sqlite_db_path, how, tol, min_snr, min_int, min_n_samples
#     except ImportError:
#         print("Invalid parameters file")
#         return
#     df = get_mz_int_depth(exported_txt_path, sqlite_db_path, target_cmpds, tol=tol, min_snr=min_snr, min_int=min_int)
#     # ask if user wants to save the dataframe
#     while True:
#         save = input("Do you want to save the dataframe? (y/n): ")
#         if save.lower() == 'y':
#             save_path = input("Please enter the path to save the dataframe: ")
#             # if it's a directory, save the file as 'depth_profile.csv' in the directory
#             if os.path.isdir(save_path):
#                 save_path = os.path.join(save_path, '2d_profile.csv')
#             # if it's not ending with '.csv', append '.csv' to the path
#             if not save_path.endswith('.csv'):
#                 save_path += '.csv'
#             df.to_csv(save_path, index=False)
#             break
#         elif save.lower() == 'n':
#             break
#         else:
#             print("Invalid input, please enter 'y' or 'n")
#
#     df = df.dropna()
#     df = df.sort_values(by='d')
#     # ask user for the horizon size
#     while True:
#         horizon_size = input("Please enter the horizon size (μm): ")
#         try:
#             horizon_size = float(horizon_size) / 10000  # convert to cm
#             break
#         except ValueError:
#             print("Invalid input, please enter a number")
#
#     chunks = get_chunks(df['d'], horizon_size, min_n_samples=min_n_samples)
#     # get the mean depth of each chunk
#     depth_1d = to_1d(df, chunks, "data['d'].mean()")
#     ratio_1d = to_1d(df, chunks, how)
#     horizon_count = [chunk[1] - chunk[0] for chunk in chunks]
#     df_1d = pd.DataFrame({'d': depth_1d, 'ratio': ratio_1d, 'horizon_count': horizon_count})
#     # ask if user wants to save the 1d depth profile
#     while True:
#         save = input("Do you want to save the 1d depth profile? (y/n): ")
#         if save.lower() == 'y':
#             save_path = input("Please enter the path to save the 1d depth profile: ")
#             # if it's a directory, save the file as 'depth_profile.csv' in the directory
#             if os.path.isdir(save_path):
#                 save_path = os.path.join(save_path, 'depth_profile.csv')
#             # if it's not ending with '.csv', append '.csv' to the path
#             if not save_path.endswith('.csv'):
#                 save_path += '.csv'
#             df_1d.to_csv(save_path, index=False)
#             break
#         elif save.lower() == 'n':
#             break
#         else:
#             print("Invalid input, please enter 'y' or 'n")


if __name__ == "__main__":
    pass
