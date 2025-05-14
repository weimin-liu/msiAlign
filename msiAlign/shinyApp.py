from shiny import App, render, ui, reactive
import matplotlib.pyplot as plt
import webbrowser
import threading
import time

from msiAlign.to1d import get_msi_depth_profile_from_gui
import os

class MSIDownCoreProfileApp:
    def __init__(self):
        self.ui = self.create_ui()
        self.server = self._server
        self.app = App(ui=self.ui, server=self.server)


    def plot_1d(self, df_1d):
        # plot the result
        df_1d = df_1d.sort_values(by='d (cm)')
        fig, ax = plt.subplots()
        ax.plot(
            df_1d['d (cm)'],
            df_1d['result']
        )
        ax.set_xlabel('Depth (cm)')
        ax.set_ylabel('Result')
        return fig



    def create_ui(self):
        return ui.page_fluid(
            ui.h1("MSI Down Core Profile Calculator"),
            ui.card(
                ui.card_header("Path to txts and metadata"),
                ui.input_text(
                    "txt_files",
                    label="Path to txt files",
                    placeholder="path/to/txt/files0;path/to/txt/files1;path/to/txt/files2",
                    width='100%'
                ),
                ui.input_text(
                    "metadata",
                    label="Path to metadata",
                    placeholder="path/to/metadata.db",
                    width = '100%'
                ),
                ui.input_text(
                    "save2d",
                    label="Path to save 2D profile",
                    placeholder="path/to/save/2d/profile",
                    width = '100%'
                ),
                ui.input_text(
                    "save1d",
                    label="Path to save 1D profile",
                    placeholder="path/to/save/1d/profile",
                    width = '100%'
                ),
            ),
            ui.card(
                ui.card_header("Spectral parameters"),
                ui.input_text(
                    "target_cmpds",
                    label="Target compounds",
                    placeholder="name1:mz1;name2:mz2",
                    width = '100%'
                ),
                ui.input_text(
                    "how",
                    label="How to calculate",
                    placeholder="data['int_name1'].sum() / (data['int_name1'].sum() + data['int_name2'].sum())",
                    width = '100%'
                ),
                ui.input_numeric(
                    "tol",
                    label="Tolerance (Da, full width)",
                    value=0.01,
                ),
                ui.input_numeric(
                    "min_snr",
                    label="Minimum SNR",
                    value=1,
                ),
                ui.input_numeric(
                    "min_int",
                    label="Minimum intensity",
                    value=1e5,
                ),
                ui.input_checkbox(
                    "normalization",
                    label="TIC Normalization",
                    value=False,
                )
            ),
            ui.card(
                ui.card_header("Spot parameters"),
                ui.input_checkbox_group(
                    "spot_method",
                    label="Spot method (choose only one)",
                    choices=['all', 'any', 'other'],
                    selected = 'all'
                ),
                ui.input_checkbox(
                    "dynamic_spots",
                    label="Dynamic spots",
                    value=False,
                ),
                ui.input_numeric(
                    "MSI_res",
                    label="MSI resolution (um)",
                    value=200,
                ),
                ui.input_numeric(
                    "max_extra_rows",
                    label="Max extra rows",
                    value = 5,
                ),
            ),

            ui.card(
                ui.card_header("Horizon parameters"),
                ui.input_numeric(
                    "min_n_spots",
                    label="Minimum number of spots per horizon",
                    value = 10
                ),
                ui.input_numeric(
                    "horizon_size",
                    label="Horizon size (um)",
                    value=500
                )

            ),
            ui.input_action_button(
                "calculate",
                label="Calculate",
                class_="btn-primary"
            ),

            ui.output_plot(
                "downcore_profile_fig",
            )
        )

    def _server(self, input, output, session):

        downcore_fig = reactive.value(None)

        @reactive.effect
        @reactive.event(input.calculate)
        def _():
            exported_txt_path = input.txt_files()
            sqlite_db_path = input.metadata()
            save_2d_path = input.save2d()
            save_1d_path = input.save1d()

            target_cmpds = input.target_cmpds()
            how = input.how()
            try:
                spot_method = input.spot_method()[0]
            except IndexError:
                spot_method = 'all'
            dynamic = input.dynamic_spots()
            tol = input.tol()
            min_snr = input.min_snr()
            min_int = input.min_int()
            min_n_samples = input.min_n_spots()
            horizon_size = input.horizon_size()
            additional_params = 'normalization:tic;' if input.normalization() else ''

            if dynamic:
                dyn_res = input.MSI_res()
                dyn_max_retry = input.max_extra_rows()
            else:
                dyn_res = 200
                dyn_max_retry = 5

            # call the function to calculate the core profile
            df_1d = get_msi_depth_profile_from_gui(
                exported_txt_path, sqlite_db_path, target_cmpds, how, spot_method, dynamic, dyn_res, dyn_max_retry, tol,
                min_snr, min_int,
                min_n_samples, horizon_size, save_2d_path, save_1d_path, additional_params, show_tk_message=False,
                return_df_1d=True
            )

            # plot the result
            downcore_fig.set(self.plot_1d(df_1d))

        @output
        @render.plot
        def downcore_profile_fig():
            if downcore_fig() is not None:
                return downcore_fig()
            else:
                return None

        @reactive.Effect
        @reactive.event(input.target_cmpds)
        def _():
            try:
                target_cmpds = input.target_cmpds()
                if target_cmpds:
                    cmpd_names = [cmpd.split(':')[0] for cmpd in target_cmpds.split(';')]
                    if len(cmpd_names) == 1:
                        how_expr = f"data['int_{cmpd_names[0]}'].mean()"
                        session.send_input_message("how", {"value": how_expr})
                    if len(cmpd_names) == 2:
                        how_expr = f"data['int_{cmpd_names[0]}'].sum() / (data['int_{cmpd_names[0]}'].sum() + data['int_{cmpd_names[1]}'].sum())"
                        session.send_input_message("how", {"value": how_expr})
            except Exception as e:
                pass

        @reactive.Effect
        @reactive.event(input.metadata)
        def _():
            try:
                sqlite_db_path = input.metadata()
                base_path = os.path.dirname(sqlite_db_path)
                if os.path.exists(base_path):
                    session.send_input_message("save2d", {"value": os.path.join(base_path, "2D.csv")})
                    session.send_input_message("save1d", {"value": os.path.join(base_path, "1D.csv")})
            except Exception as e:
                pass


def run_app():
    app = MSIDownCoreProfileApp()

    # Run the app in a separate thread to avoid blocking
    def start_server():
        app.app.run(port=61234)

    threading.Thread(target=start_server, daemon=True).start()

    # Give the server a moment to start
    time.sleep(1)

    # Open the app in a web browser
    webbrowser.open("http://localhost:61234")

if __name__ == "__main__":
    pass