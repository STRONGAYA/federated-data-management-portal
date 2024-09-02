import dash
import json
import os

import dash_bootstrap_components as dbc
import plotly.io as pio

from apscheduler.schedulers.background import BackgroundScheduler
from dash.dependencies import MATCH
from dash.dependencies import Input, Output
from dash import html, dcc

# internal dependencies
import src.callbacks as callbacks
from src.misc import fetch_data

pio.templates.default = 'seaborn'
page_title = 'STRONG-AYA | Data Management Portal'


class Dashboard:
    def __init__(self, json_file_path):
        """
        Initialize the Dashboard class.

        This constructor method initializes the Dashboard class with a given JSON file path.
        It loads data from the JSON file, sets up the Dash app with a layout and title, and registers callbacks.

        Parameters:
        json_file_path (str): The path to the JSON file to load data from.

        Raises:
        SystemExit: If the provided file path does not end with '.json'.
        """
        if json_file_path.endswith('.json'):
            with open(json_file_path, 'r') as f:
                self.global_schema_data = json.load(f)
        else:
            exit('Invalid schema file path')

        # refers to <folder_with_this_file>/assets/dashboard_aesthetics.css
        self.App = dash.Dash(__name__, pages_folder="pages", use_pages=True,
                             external_stylesheets=['dashboard_aesthetics.css', dbc.themes.BOOTSTRAP])

        self.App.layout = self.define_layout()
        self.App._favicon = f'..{os.path.sep}assets{os.path.sep}favicon.ico'
        self.register_callbacks()

    def define_layout(self):
        return html.Div([
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='store'),
            dcc.Store(id='data-availability-store-1'),
            html.Div([
                dcc.Link('Data availability', href='/data-availability'),
                dcc.Link('Missing Data', href='/data-missingness')
            ]),
            dash.page_container
        ])

    def register_callbacks(self):
        """"""
        @self.App.callback(
            Output('url', 'pathname'),
            [Input('go-to-home', 'n_clicks'),
             Input('go-to-missing-data', 'n_clicks')]
        )
        def navigate(n_clicks_home, n_clicks_missing_data):
            ctx = dash.callback_context
            if not ctx.triggered:
                return dash.no_update
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if button_id == 'go-to-home':
                return '/'
            elif button_id == 'go-to-missing-data':
                return '/missing-data'
            return dash.no_update

        @self.App.callback(
            Output('tile-content-1', 'children'),
            [Input('store', 'data')]
        )
        def update_tile_content_1(descriptive_data):
            """
            Callback function to update the content of the first tile.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `fetch_total_sample_size` function from the `callbacks` module,
            passing the `descriptive_data` as an argument.
            The result of the `update_tile_content_1` function is then returned by the `update_tile_1` function,
             which updates the 'tile-content-1' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            The result of the `update_tile_content_1` function from the `callbacks` module.
            """
            return callbacks.fetch_total_sample_size(descriptive_data)

        @self.App.callback(
            Output('tile-content-2', 'children'),
            [Input('store', 'data')]
        )
        def update_tile_content_2(descriptive_data):
            """
            Callback function to update the content of the second tile.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `fetch_number_of_keys` function from the `callbacks` module,
            passing the `descriptive_data` as an argument.
            The result of the `fetch_number_of_keys` function is then returned by the `update_tile_content_2` function,
             which updates the 'tile-content-2' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            The result of the `fetch_number_of_keys` function from the `callbacks` module.
            """
            return callbacks.fetch_number_of_keys(descriptive_data)

        @self.App.callback(
            Output('tile-content-3', 'children'),
            [Input('store', 'data')]
        )
        def update_tile_content_3(descriptive_data):
            """
            Callback function to update the content of the third tile.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `fetch_total_sample_size` function from the `callbacks` module,
            passing the `descriptive_data` as an argument.
            The result of the `fetch_total_sample_size` function is then returned by the `update_tile_content_3` function,
            which updates the 'tile-content-3' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            The result of the `fetch_total_sample_size` function from the `callbacks` module.
            """
            return callbacks.fetch_field_count(descriptive_data)

        @self.App.callback(
            Output({'type': 'dynamic-donut-one', 'index': MATCH}, 'figure'),
            [Input('store', 'data')]
        )
        def update_sample_size_info(descriptive_data):
            """
            Callback function to update the sample size information in the donut chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_donut_chart` function from the `callbacks` module,
            passing the `descriptive_data` and the chart type as arguments.
            The result of the `generate_donut_chart` function is then returned by the `update_sample_size_info` function,
            which updates the 'dynamic-donut-one' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            plotly.graph_objs._figure.Figure: The updated donut chart figure.
            """
            return callbacks.generate_donut_chart(descriptive_data, chart_type="organisation")

        @self.App.callback(
            Output({'type': 'dynamic-donut-two', 'index': MATCH}, 'figure'),
            [Input('store', 'data')]
        )
        def update_country_donut_chart(descriptive_data):
            """
            Callback function to update the country donut chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_donut_chart` function from the `callbacks` module,
            passing the `descriptive_data` and the chart type as arguments.
            The result of the `generate_donut_chart` function is then returned by the `update_country_donut_chart` function,
            which updates the 'dynamic-donut-two' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            plotly.graph_objs._figure.Figure: The updated donut chart figure.
            """
            return callbacks.generate_donut_chart(descriptive_data, chart_type="country")

        @self.App.callback(
            [Output({'type': 'dynamic-donut-one', 'index': MATCH}, 'style'),
             Output({'type': 'dynamic-donut-two', 'index': MATCH}, 'style')],
            [Input({'type': 'dynamic-donut-one', 'index': MATCH}, 'figure'),
             Input({'type': 'dynamic-donut-two', 'index': MATCH}, 'figure')]
        )
        def update_graph_style(figure_one, figure_two):
            """
            Callback function to update the style of the donut charts.

            This function is triggered whenever the figures in the 'dynamic-donut-one' and 'dynamic-donut-two' components change.
            It calculates the length of the legends in the figures and uses this to calculate the height of the dcc.Graph components.
            The function then returns the new styles for the 'dynamic-donut-one' and 'dynamic-donut-two' components.

            Parameters:
            figure_one (plotly.graph_objs._figure.Figure): The figure in the 'dynamic-donut-one' component.
            figure_two (plotly.graph_objs._figure.Figure): The figure in the 'dynamic-donut-two' component.

            Returns:
            dict: The new style for the 'dynamic-donut-one' component.
            dict: The new style for the 'dynamic-donut-two' component.
            """
            # Calculate the length of the legends
            legend_length_one = len(figure_one['data'][0]['labels'])
            legend_length_two = len(figure_two['data'][0]['labels'])

            # Calculate the height of the dcc.Graph components based on the length of the legends
            height_one = max(400, legend_length_one * 20 + 200)
            height_two = max(400, legend_length_two * 20 + 200)

            # Return the new styles
            return {'height': f'{height_one}px'}, {'height': f'{height_two}px'}

        @self.App.callback(
            [Output('tile-content-6', 'children'),
             Output('data-availability-store-1', 'data')],
            [Input('store', 'data')]
        )
        def update_data_availability_table(descriptive_data):
            """
            Callback function to update the data availability table.

            This function is triggered whenever the data in the 'store' component changes.
            It calls a function from the `callbacks` module, passing the `descriptive_data` as an argument.
            The result of this function is then returned by the `update_data_availability_table` function,
            which updates the 'tile-content-5' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            The result of the function from the `callbacks` module.
            """
            df, dash_table = callbacks.generate_fair_data_availability(self.global_schema_data, descriptive_data)
            return dash_table, df.to_json(date_format='iso', orient='split')

        @self.App.callback(
            Output({'type': 'dynamic-bar', 'index': MATCH}, 'figure'),
            [Input('data-availability-store-1', 'data')]
        )
        def update_completeness_info(availability_data):
            """
            Callback function to update the completeness chart.

            This function is triggered whenever the data in the 'data-availability-store-1' component changes.
            It calls the `generate_completeness_chart` function from the `callbacks` module,
            passing the `availability_data` as an argument.
            The result of the `generate_completeness_chart` function is then returned by the `update_completeness_info` function,
            which updates the 'dynamic-bar' component in the Dash app.

            Parameters:
            availability_data (str): The data stored in the 'data-availability-store-1' component.
                                     This is a JSON string representing a DataFrame.

            Returns:
            plotly.graph_objs._figure.Figure: The updated completeness chart figure.
            """
            return callbacks.generate_completeness_chart(availability_data)

    def run(self, debug=None):
        """
        Start the Plotly Dash dashboard

        :param bool debug: specify whether to use debugging mode
        """
        if isinstance(debug, bool) is False:
            debug = False

        self.App.run_server(debug=debug, dev_tools_ui=False, host='0.0.0.0')


if __name__ == '__main__':
    json_file_path = os.getenv('JSON_FILE_PATH')
    if json_file_path:
        dash_app = Dashboard(json_file_path)
        vantage6_config = None
    else:
        # This allows the user to provide the path to the global schema and Vantage6 config when not running in Docker
        config_path = input("Please provide the path to the Vantage6 configuration JSON file "
                            "or press enter to use mock data.\n")
        json_file_path = input("Please provide the path to the global schema JSON file.\n")
        dash_app = Dashboard(json_file_path)

        if config_path and config_path.endswith('.json'):
            with open(config_path, 'r') as f:
                vantage6_config = json.load(f)
        else:
            vantage6_config = None

    # Call the fetch_data function immediately at startup
    dash_app.App.layout['store'].data = fetch_data(vantage6_config, None)

    # Run the fetch_data function every six days
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: setattr(dash_app.App.layout['store'], 'data',
                                      fetch_data(vantage6_config, dash_app.App.layout['store'].data)),
                      'interval', seconds=518400)
    scheduler.start()

    dash_app.run()
