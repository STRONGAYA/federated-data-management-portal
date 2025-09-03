import copy
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
                self.global_semantic_map_data = json.load(f)
        else:
            exit('Invalid semantic_map file path')

        # Set default max_depth for semantic_map category extraction
        self.max_depth = 1

        # refers to <folder_with_this_file>/assets/dashboard_aesthetics.css
        self.App = dash.Dash(__name__, pages_folder="pages", use_pages=True,
                             external_stylesheets=['dashboard_aesthetics.css', dbc.themes.BOOTSTRAP])

        self.App.layout = self.define_layout()
        self.App._favicon = f'..{os.path.sep}assets{os.path.sep}favicon.ico'
        self.register_callbacks()

    def extract_categories_from_semantic_map(self, max_depth=0):
        """
        Extract categories from semantic_map_reconstruction hierarchy for filtering.
        
        Parameters:
        max_depth (int): Maximum depth to traverse in semantic_map_reconstruction (default: 2)
        
        Returns:
        list: List of unique category labels with their corresponding values for filtering
        """
        categories = set()
        
        if 'variable_info' not in self.global_semantic_map_data:
            return []
            
        for variable_name, variable_data in self.global_semantic_map_data['variable_info'].items():
            if 'schema_reconstruction' in variable_data and variable_data['schema_reconstruction']:
                # Process each level in schema_reconstruction up to max_depth
                # Only look at class items (not nodes) within the specified depth
                for level, reconstruction_item in enumerate(variable_data['schema_reconstruction']):
                    if level >= max_depth:
                        break
                    
                    if (reconstruction_item.get('type') == 'class' and 
                        'aesthetic_label' in reconstruction_item and
                        reconstruction_item.get('placement') != 'before'):
                        # Remove underscores and format the aesthetic label nicely
                        aesthetic_label = reconstruction_item['aesthetic_label'].replace('_', ' ')
                        categories.add(f" {aesthetic_label}")
        
        return sorted(list(categories))

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
        def update_organisation_availability_chart(descriptive_data):
            """
            Callback function to update the sample size information in the donut chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_donut_chart` function from the `callbacks` module,
            passing the `descriptive_data` and the chart type as arguments.
            The result of the `generate_donut_chart` function is then returned by the `update_organisation_availability_chart` function,
            which updates the 'dynamic-donut-one' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            plotly.graph_objs._figure.Figure: The updated donut chart figure.
            """
            return callbacks.generate_donut_chart(descriptive_data, chart_domain='availability',
                                                  chart_type="organisation")

        @self.App.callback(
            Output({'type': 'dynamic-donut-two', 'index': MATCH}, 'figure'),
            [Input('store', 'data')]
        )
        def update_country_availability_chart(descriptive_data):
            """
            Callback function to update the country donut chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_donut_chart` function from the `callbacks` module,
            passing the `descriptive_data` and the chart type as arguments.
            The result of the `generate_donut_chart` function is then returned by the `update_country_availability_chart` function,
            which updates the 'dynamic-donut-two' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            plotly.graph_objs._figure.Figure: The updated donut chart figure.
            """
            return callbacks.generate_donut_chart(descriptive_data, chart_domain='availability', chart_type="country")

        @self.App.callback(
            Output({'type': 'dynamic-donut-three', 'index': MATCH}, 'figure'),
            [Input('store', 'data')]
        )
        def update_organisation_completeness_chart(descriptive_data):
            """
            Callback function to update the completeness information in the donut chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_donut_chart` function from the `callbacks` module,
            passing the `descriptive_data` and the chart type as arguments.
            The result of the `generate_donut_chart`
            function is then returned by the `update_organisation_completeness_chart` function,
            which updates the 'dynamic-donut-three' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            plotly.graph_objs._figure.Figure: The updated donut chart figure.
            """
            return callbacks.generate_donut_chart(descriptive_data, chart_domain='completeness',
                                                  chart_type="organisation")

        @self.App.callback(
            Output({'type': 'dynamic-donut-four', 'index': MATCH}, 'figure'),
            [Input('store', 'data')]
        )
        def update_country_completeness_chart(descriptive_data):
            """
            Callback function to update the completeness information in the donut chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_donut_chart` function from the `callbacks` module,
            passing the `descriptive_data` and the chart type as arguments.
            The result of the `generate_donut_chart`
            function is then returned by the `update_country_completeness_chart` function,
            which updates the 'dynamic-donut-four' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            plotly.graph_objs._figure.Figure: The updated donut chart figure.
            """
            return callbacks.generate_donut_chart(descriptive_data, chart_domain='completeness',
                                                  chart_type="country")

        @self.App.callback(
            Output({'type': 'dynamic-donut-five', 'index': MATCH}, 'figure'),
            [Input('store', 'data')]
        )
        def update_organisation_plausibility_chart(descriptive_data):
            """
            Callback function to update the plausibility information in the donut chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_donut_chart` function from the `callbacks` module,
            passing the `descriptive_data` and the chart type as arguments.
            The result of the `generate_donut_chart`
            function is then returned by the `update_organisation_plausibility_chart` function,
            which updates the 'dynamic-donut-five' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            plotly.graph_objs._figure.Figure: The updated donut chart figure.
            """
            return callbacks.generate_donut_chart(descriptive_data, chart_domain='plausibility',
                                                  chart_type="organisation")

        @self.App.callback(
            Output({'type': 'dynamic-donut-six', 'index': MATCH}, 'figure'),
            [Input('store', 'data')]
        )
        def update_country_plausibility_chart(descriptive_data):
            """
            Callback function to update the plausibility information in the donut chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_donut_chart` function from the `callbacks` module,
            passing the `descriptive_data` and the chart type as arguments.
            The result of the `generate_donut_chart`
            function is then returned by the `update_country_plausibility_chart` function,
            which updates the 'dynamic-donut-six' component in the Dash app.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.

            Returns:
            plotly.graph_objs._figure.Figure: The updated donut chart figure.
            """
            return callbacks.generate_donut_chart(descriptive_data, chart_domain='plausibility',
                                                  chart_type="country")

        @self.App.callback(
            [Output({'type': 'dynamic-donut-one', 'index': MATCH}, 'style'),
             Output({'type': 'dynamic-donut-two', 'index': MATCH}, 'style'),
             Output({'type': 'dynamic-donut-three', 'index': MATCH}, 'style'),
             Output({'type': 'dynamic-donut-four', 'index': MATCH}, 'style'),
             Output({'type': 'dynamic-donut-five', 'index': MATCH}, 'style'),
             Output({'type': 'dynamic-donut-six', 'index': MATCH}, 'style')],
            [Input({'type': 'dynamic-donut-one', 'index': MATCH}, 'figure'),
             Input({'type': 'dynamic-donut-two', 'index': MATCH}, 'figure'),
             Input({'type': 'dynamic-donut-three', 'index': MATCH}, 'figure'),
             Input({'type': 'dynamic-donut-four', 'index': MATCH}, 'figure'),
             Input({'type': 'dynamic-donut-five', 'index': MATCH}, 'figure'),
             Input({'type': 'dynamic-donut-sex', 'index': MATCH}, 'figure')]
        )
        def update_graph_style(figure_one, figure_two, figure_three, figure_four):
            """
            Callback function to update the style of the donut charts.

            This function is triggered whenever the figures in the 'dynamic-donut-one' and 'dynamic-donut-two' components change.
            It calculates the length of the legends in the figures and uses this to calculate the height of the dcc.Graph components.
            The function then returns the new styles for the 'dynamic-donut-one' and 'dynamic-donut-two' components.

            Parameters:
            figure_one (plotly.graph_objs._figure.Figure): The figure in the 'dynamic-donut-one' component.
            figure_two (plotly.graph_objs._figure.Figure): The figure in the 'dynamic-donut-two' component.
            figure_three (plotly.graph_objs._figure.Figure): The figure in the 'dynamic-donut-three' component.
            figure_four (plotly.graph_objs._figure.Figure): The figure in the 'dynamic-donut-four' component.

            Returns:
            dict: The new style for the 'dynamic-donut-one' component.
            dict: The new style for the 'dynamic-donut-two' component.
            dict: The new style for the 'dynamic-donut-three' component.
            dict: The new style for the 'dynamic-donut-four' component.
            """
            # Calculate the length of the legends
            legend_length_one = len(figure_one['data'][0]['labels'])
            legend_length_two = len(figure_two['data'][0]['labels'])
            legend_length_three = len(figure_three['data'][0]['labels'])
            legend_length_four = len(figure_four['data'][0]['labels'])

            # Calculate the height of the dcc.Graph components based on the length of the legends
            height_one = max(400, legend_length_one * 20 + 200)
            height_two = max(400, legend_length_two * 20 + 200)
            height_three = max(400, legend_length_three * 20 + 200)
            height_four = max(400, legend_length_four * 20 + 200)

            # Return the new styles
            return ({'height': f'{height_one}px'}, {'height': f'{height_two}px'},
                    {'height': f'{height_three}px'}, {'height': f'{height_four}px'})

        @self.App.callback(
            [Output('tile-content-6', 'children'),
             Output('data-availability-store-1', 'data')],
            [Input('store', 'data'),
             Input('subset-prefix-selection-checkboxes', 'value')]
        )
        def update_data_availability_table(descriptive_data, prefix_selection):
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
            # Create filtered copies to avoid modifying originals
            _descriptive_data = callbacks.filter_descriptive_data_by_semantic_map_categories(descriptive_data,
                                                                  prefix_selection, self.global_semantic_map_data, max_depth=self.max_depth) if prefix_selection else descriptive_data

            # Filter global semantic_map data
            filtered_semantic_map = copy.deepcopy(self.global_semantic_map_data)
            if prefix_selection:
                # Get variables that belong to selected categories
                selected_variables = set()
                category_mapping = {cat: cat.replace('_', ' ').title() for cat in prefix_selection}
                
                for variable_name, variable_data in filtered_semantic_map['variable_info'].items():
                    if 'schema_reconstruction' in variable_data:
                        for level, reconstruction_item in enumerate(variable_data['schema_reconstruction']):
                            if level >= 2:  # max_depth
                                break
                            
                            if (reconstruction_item.get('type') == 'class' and 
                                'aesthetic_label' in reconstruction_item and
                                reconstruction_item.get('placement') != 'after'):
                                # Remove underscores from aesthetic label and normalize
                                aesthetic_label = reconstruction_item['aesthetic_label'].replace('_', ' ')
                                for cat_value, cat_label in category_mapping.items():
                                    if aesthetic_label.lower() == cat_label.lower():
                                        selected_variables.add(variable_name)
                                        break
                
                filtered_semantic_map['variable_info'] = {
                    var: info for var, info in filtered_semantic_map['variable_info'].items()
                    if var in selected_variables
                }

            # Generate table with filtered data
            df, dash_table = callbacks.generate_fair_data_availability(filtered_semantic_map, _descriptive_data)
            return dash_table, df.to_json()

        @self.App.callback(
            [Output('subset-selection-checkboxes', 'options'),
             Output('country-selection-checkboxes', 'options'),
             Output('subset-selection-checkboxes', 'value'),
             Output('country-selection-checkboxes', 'value')],
            [Input('store', 'data'),
             Input('subset-selection-checkboxes', 'value'),
             Input('country-selection-checkboxes', 'value')]
        )
        def update_checkboxes(descriptive_data, selected_organisations, selected_countries):
            """
            Callback function to update the options for the organisation selection checkboxes and
            country selection checkboxes.

            This function is triggered whenever the data in the 'store' component changes or
            when the user selects an organisation or country.
            It extracts the latest data from the descriptive data and generates a list of options for
            the checkboxes based on the keys in the latest data.
            It also ensures that the selections in the two checkboxes are linked.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
                                     Each key is a timestamp,
                                     and each value is a dictionary containing the data fetched at that timestamp.
            selected_organisations (list): The currently selected organisations.
            selected_countries (list): The currently selected countries.

            Returns:
            list: A list of dictionaries representing the options for the organisation checkboxes.
            list: A list of dictionaries representing the options for the country checkboxes.
            list: The updated selected organisations.
            list: The updated selected countries.
            """
            # Get the latest data
            latest_data = descriptive_data[max(descriptive_data.keys())]

            # Generate options for organisations and countries
            organisation_options = [{'label': f'{k}', 'value': k} for k in latest_data.keys()]
            country_options = [{'label': f'{v["country"]}', 'value': v['country'], 'disabled': True}
                               for k, v in latest_data.items()]

            # Ensure unique country options
            country_options = [dict(t) for t in {tuple(d.items()) for d in country_options}]

            # Update selected organisations and countries based on the selections
            if selected_organisations:
                selected_countries = list(set([latest_data[org]['country'] for org in selected_organisations]))
            elif selected_countries:
                selected_organisations = [org for org, data in latest_data.items() if
                                          data['country'] in selected_countries]

            return (organisation_options, country_options,
                    selected_organisations, selected_countries)

        @self.App.callback(
            Output('subset-prefix-selection-checkboxes', 'options'),
            Output('subset-prefix-selection-checkboxes', 'value'),
            [Input('store', 'data')]
        )
        def update_table_prefix_options(descriptive_data):
            """Updates the prefix selection options with categories extracted from semantic_map."""
            # Extract categories dynamically from semantic_map
            semantic_map_categories = self.extract_categories_from_semantic_map(max_depth=self.max_depth)
            prefix_options = [{'label': category, 'value': category.lower().replace(' ', '_')} for category in semantic_map_categories]
            return prefix_options, []

        @self.App.callback(
            Output({'type': 'dynamic-completeness-bar', 'index': MATCH}, 'figure'),
            [Input('store', 'data'),
             Input('subset-selection-checkboxes', 'value'),
             Input('subset-prefix-selection-checkboxes', 'value')]
        )
        def update_variable_completeness_info(descriptive_data, selection, prefix_selection):
            """
            Callback function to update the completeness chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_variable_bar_chart` function from the `callbacks` module,
            passing the `availability_data` as an argument.
            The result of the `generate_variable_bar_chart` function is then returned by
            the `update_variable_completeness_info` function,
            which updates the 'dynamic-completeness-bar' component in the Dash app.

            Parameters:
            descriptive_data (str): The data stored in the 'store' component.
                                    This is a JSON string representing a DataFrame.

            Returns:
            plotly.graph_objs._figure.Figure: The updated completeness chart figure.
            """
            if selection:
                _descriptive_data = copy.deepcopy(descriptive_data)
                for timestamp in descriptive_data.keys():
                    for org in descriptive_data[timestamp].keys():
                        if org not in selection:
                            del _descriptive_data[timestamp][org]

                # Filter data based on selected prefixes
                _descriptive_data = callbacks.filter_descriptive_data_by_semantic_map_categories(_descriptive_data, prefix_selection, self.global_semantic_map_data, max_depth=self.max_depth)

                return callbacks.generate_variable_bar_chart(_descriptive_data, domain='completeness')
            else:
                return callbacks.generate_unavailable_organisation_annotation(domain='completeness')

        @self.App.callback(
            Output({'type': 'dynamic-plausibility-bar', 'index': MATCH}, 'figure'),
            [Input('store', 'data'),
             Input('subset-selection-checkboxes', 'value'),
             Input('subset-prefix-selection-checkboxes', 'value')]
        )
        def update_variable_plausibility_info(descriptive_data, selection, prefix_selection):
            """
            Callback function to update the plausibility chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_variable_bar_chart` function from the `callbacks` module,
            passing the `availability_data` as an argument.
            The result of the `generate_variable_bar_chart` function is then returned by
            the `update_variable_plausibility_info` function,
            which updates the 'dynamic-plausibility-bar' component in the Dash app.

            Parameters:
            descriptive_data (str): The data stored in the 'store' component.
                                    This is a JSON string representing a DataFrame.

            Returns:
            plotly.graph_objs._figure.Figure: The updated plausibility chart figure.
            """
            if selection:
                _descriptive_data = copy.deepcopy(descriptive_data)
                for timestamp in descriptive_data.keys():
                    for org in descriptive_data[timestamp].keys():
                        if org not in selection:
                            del _descriptive_data[timestamp][org]

                # Filter data based on selected prefixes
                _descriptive_data = callbacks.filter_descriptive_data_by_semantic_map_categories(_descriptive_data, prefix_selection, self.global_semantic_map_data, max_depth=self.max_depth)

                return callbacks.generate_variable_bar_chart(_descriptive_data, domain='plausibility')
            else:
                return callbacks.generate_unavailable_organisation_annotation(domain='plausibility')

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
        # This allows the user to provide the path to the global semantic_map and Vantage6 config when not running in Docker
        config_path = input("Please provide the path to the Vantage6 configuration JSON file "
                            "or press enter to use mock data.\n")
        if len(config_path) == 0:
            json_file_path = os.path.join(os.getcwd(), 'example_data', 'schema.json')
        else:
            json_file_path = input("Please provide the path to the global semantic_map JSON file.\n")
        dash_app = Dashboard(json_file_path)

        if config_path and config_path.endswith('.json'):
            with open(config_path, 'r') as f:
                vantage6_config = json.load(f)
        else:
            vantage6_config = None

    # Call the fetch_data function immediately at startup
    dash_app.App.layout['store'].data = fetch_data(vantage6_config, None,
                                                   dash_app.global_semantic_map_data['variable_info'])

    # Run the fetch_data function every six days
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: setattr(dash_app.App.layout['store'], 'data',
                                      fetch_data(vantage6_config, dash_app.App.layout['store'].data)),
                      'interval', seconds=518400)
    scheduler.start()

    dash_app.run()
