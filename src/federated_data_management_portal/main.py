import copy
import dash
import json
import os
from datetime import datetime
from pathlib import Path

import dash_bootstrap_components as dbc
import plotly.io as pio

from dash.dependencies import MATCH
from dash.dependencies import Input, Output, State
from dash import html, dcc
from flask import request

from federated_data_management_portal import callbacks
from federated_data_management_portal.auth import authenticated_email_from_headers

# Own template based on seaborn, with the hover crosshair disabled:
# dragmode=False removes the crosshair cursor (and drag-zoom) on every
# chart, and spikes are explicitly off
pio.templates['portal'] = copy.deepcopy(pio.templates['seaborn'])
pio.templates.default = 'portal'
pio.templates['portal'].layout.dragmode = False
pio.templates['portal'].layout.xaxis.showspikes = False
pio.templates['portal'].layout.yaxis.showspikes = False
page_title = 'STRONG-AYA | Data Management Portal'
PACKAGE_ROOT = Path(__file__).resolve().parent

# Reserved top-level key holding the central (aggregating) task results
AGGREGATE_SECTION_KEY = 'aggregate'


def load_json_file(json_file_path):
    """Load a JSON or JSON-LD file and fail with a clear message when the path is invalid."""
    if not json_file_path:
        raise SystemExit('A JSON file path is required.')

    path = Path(json_file_path).expanduser()
    if path.suffix not in ('.json', '.jsonld'):
        raise SystemExit(f'Expected a .json or .jsonld file, got: {path}')
    if not path.exists():
        raise SystemExit(f'JSON file does not exist: {path}')

    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def is_timestamp_key(value):
    """Return whether a JSON object key can be treated as a dashboard timestamp."""
    try:
        datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def load_static_dashboard_data(dashboard_data_file_path):
    """
    Load dashboard data in the shape expected by the Dash callbacks.

    The required static format is:
    {
      "2026-01-01T00:00:00": {
        "Organisation name": {
          "country": "Country",
          "sample_size": 123,
          "categorical": "{...}",
          "numerical": "{...}"
        }
      },
      "aggregate": {
        "2026-01-01T00:00:00": {
          "categorical": "{...}",
          "numerical": "{...}"
        }
      }
    }

    Top-level keys must be ISO timestamps so exported dashboard snapshots retain
    when the data was generated. The reserved 'aggregate' key is the one
    exception: it holds the central (aggregating) task results, itself keyed by
    ISO timestamps.
    """
    dashboard_data = load_json_file(dashboard_data_file_path)

    if not isinstance(dashboard_data, dict):
        raise SystemExit('Dashboard data JSON must contain an object at the top level.')

    invalid_timestamp_keys = [key for key in dashboard_data.keys()
                              if key != AGGREGATE_SECTION_KEY and not is_timestamp_key(key)]
    if invalid_timestamp_keys:
        keys = ', '.join(str(key) for key in invalid_timestamp_keys[:3])
        raise SystemExit(f'Dashboard data top-level keys must be ISO timestamps. Invalid key(s): {keys}')

    aggregate_section = dashboard_data.get(AGGREGATE_SECTION_KEY, {})
    if not isinstance(aggregate_section, dict):
        raise SystemExit(f'The "{AGGREGATE_SECTION_KEY}" section must contain an object keyed by ISO timestamps.')
    invalid_aggregate_keys = [key for key in aggregate_section.keys() if not is_timestamp_key(key)]
    if invalid_aggregate_keys:
        keys = ', '.join(str(key) for key in invalid_aggregate_keys[:3])
        raise SystemExit(f'The "{AGGREGATE_SECTION_KEY}" section keys must be ISO timestamps. Invalid key(s): {keys}')

    return dashboard_data


def split_aggregate_section(dashboard_data):
    """
    Split the reserved top-level 'aggregate' section from the timestamped
    organisation snapshots.

    Existing callbacks iterate over the top-level keys as timestamps, so the
    central aggregate results are kept apart and served through their own store.

    Parameters:
    dashboard_data (dict): The full dashboard data including the optional
                           'aggregate' section.

    Returns:
    tuple: (snapshots, aggregate_section) where snapshots maps ISO timestamps to
           organisation data and aggregate_section maps ISO timestamps to the
           central results.
    """
    aggregate_section = dashboard_data.get(AGGREGATE_SECTION_KEY, {})
    snapshots = {key: value for key, value in dashboard_data.items() if key != AGGREGATE_SECTION_KEY}
    return snapshots, aggregate_section




def _present_classes(descriptive_data):
    """Collect the variable class codes present in the latest snapshot."""
    latest_data = descriptive_data[max(descriptive_data.keys())]
    present = set()
    for org_data in latest_data.values():
        categorical, numerical = callbacks._load_organization_stats(org_data)
        present.update(categorical['variable'].unique())
        present.update(numerical['variable'].unique())
    return present


class Dashboard:
    def __init__(self, schema_file_path, dashboard_data_file_path):
        """
        Initialize the Dashboard class.

        This constructor method initializes the Dashboard class with local files.
        It loads the JSON-LD schema and the static dashboard data, sets up the Dash app
        with a layout and title, and registers callbacks.

        Parameters:
        schema_file_path (str): The path to the schema JSON-LD file.
        dashboard_data_file_path (str): The path to the static dashboard data JSON file.
        """
        self.global_semantic_map_data = load_json_file(schema_file_path)
        self.dashboard_data, self.aggregate_data = split_aggregate_section(
            load_static_dashboard_data(dashboard_data_file_path))

        # Set default max_depth for semantic_map category extraction
        self.max_depth = 1

        # Dash automatically loads CSS and other static files from the assets directory.
        self.App = dash.Dash(__name__, pages_folder=str(PACKAGE_ROOT / "pages"),
                             assets_folder=str(PACKAGE_ROOT / "assets"), use_pages=True,
                             external_stylesheets=[dbc.themes.BOOTSTRAP])

        self.App.layout = self.define_layout()
        self.App._favicon = 'info-portal/favicon.png'
        self.register_callbacks()

    def define_layout(self):
        return html.Div([
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='store', data=self.dashboard_data),
            dcc.Store(id='aggregate-store', data=self.aggregate_data),
            dcc.Store(id='data-availability-store-1'),
            dash.page_container
        ])

    def register_callbacks(self):
        """"""

        @self.App.callback(
            Output('authenticated-user-email', 'children'),
            Input('url', 'pathname')
        )
        def show_authenticated_user(_pathname):
            """Display identity metadata forwarded by the authentication proxy."""
            return authenticated_email_from_headers(request.headers)

        @self.App.callback(
            Output('authenticated-user-container', 'hidden'),
            Input('authenticated-user-email', 'children')
        )
        def show_authenticated_user_actions(email):
            """Show account actions only when proxy identity metadata is present."""
            return not bool(email)

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
             Input({'type': 'dynamic-donut-six', 'index': MATCH}, 'figure')]
        )
        def update_graph_style(figure_one, figure_two, figure_three, figure_four, figure_five, figure_six):
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
            legend_length_five = len(figure_five['data'][0]['labels'])
            legend_length_six = len(figure_six['data'][0]['labels'])

            # Calculate the height of the dcc.Graph components based on the length of the legends
            height_one = max(400, legend_length_one * 20 + 200)
            height_two = max(400, legend_length_two * 20 + 200)
            height_three = max(400, legend_length_three * 20 + 200)
            height_four = max(400, legend_length_four * 20 + 200)
            height_five = max(400, legend_length_five * 20 + 200)
            height_six = max(400, legend_length_six * 20 + 200)

            # Return the new styles
            return ({'height': f'{height_one}px'}, {'height': f'{height_two}px'},
                    {'height': f'{height_three}px'}, {'height': f'{height_four}px'},
                    {'height': f'{height_five}px'}, {'height': f'{height_six}px'})

        @self.App.callback(
            [Output('tile-content-6', 'children'),
             Output('data-availability-store-1', 'data')],
            [Input('store', 'data'),
             Input('availability-variable-dropdown', 'value')]
        )
        def update_data_availability_table(descriptive_data, variable_selection):
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
            _options, var_info = callbacks.build_variable_options(
                self.global_semantic_map_data, _present_classes(descriptive_data))
            selected_classes = callbacks.resolve_variable_selection(variable_selection, var_info)

            # Filter global semantic_map data
            filtered_semantic_map = copy.deepcopy(self.global_semantic_map_data)
            if selected_classes is not None:
                variables_to_remove = []
                for variable_name, variable_data in filtered_semantic_map['schema']['variables'].items():
                    if variable_data.get('class') not in selected_classes:
                        variables_to_remove.append(variable_name)

                for variable_name in variables_to_remove:
                    filtered_semantic_map['schema']['variables'].pop(variable_name)

            # Generate table with filtered data
            df, dash_table = callbacks.generate_fair_data_availability(filtered_semantic_map, descriptive_data,
                                                                       selected_classes=selected_classes)
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
            Output({'type': 'dynamic-completeness-bar', 'index': MATCH}, 'figure'),
            [Input('store', 'data'),
             Input('subset-selection-checkboxes', 'value'),
             Input('completeness-variable-dropdown', 'value'),
             Input('completeness-view-store', 'data')]
        )
        def update_variable_completeness_info(descriptive_data, selection, variable_selection, view):
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

                _options, var_info = callbacks.build_variable_options(
                    self.global_semantic_map_data, _present_classes(_descriptive_data))
                selected_classes = callbacks.resolve_variable_selection(variable_selection, var_info)

                if view == 'pie':
                    return callbacks.generate_variable_donut_chart(_descriptive_data, domain='completeness',
                                                                   semantic_map_data=self.global_semantic_map_data)
                return callbacks.generate_variable_bar_chart(_descriptive_data, domain='completeness',
                                                             semantic_map_data=self.global_semantic_map_data,
                                                             selected_classes=selected_classes)
            else:
                return callbacks.generate_unavailable_organisation_annotation(domain='completeness')

        @self.App.callback(
            Output({'type': 'dynamic-plausibility-bar', 'index': MATCH}, 'figure'),
            [Input('store', 'data'),
             Input('subset-selection-checkboxes', 'value'),
             Input('plausibility-variable-dropdown', 'value'),
             Input('plausibility-view-store', 'data')]
        )
        def update_variable_plausibility_info(descriptive_data, selection, variable_selection, view):
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

                _options, var_info = callbacks.build_variable_options(
                    self.global_semantic_map_data, _present_classes(_descriptive_data))
                selected_classes = callbacks.resolve_variable_selection(variable_selection, var_info)

                if view == 'pie':
                    return callbacks.generate_variable_donut_chart(_descriptive_data, domain='plausibility',
                                                                   semantic_map_data=self.global_semantic_map_data)
                return callbacks.generate_variable_bar_chart(_descriptive_data, domain='plausibility',
                                                             semantic_map_data=self.global_semantic_map_data,
                                                             selected_classes=selected_classes)
            else:
                return callbacks.generate_unavailable_organisation_annotation(domain='plausibility')

        @self.App.callback(
            Output('availability-over-time', 'figure'),
            [Input('store', 'data'),
             Input('availability-over-time-variable-dropdown', 'value')]
        )
        def update_availability_over_time(descriptive_data, variable_selection):
            """
            Callback function to update the data availability over time chart.

            This function is triggered whenever the data in the 'store' component changes.
            It calls the `generate_sample_size_over_time_chart` function from the `callbacks`
            module with the stored data, which stacks the sample sizes of all organisations
            per snapshot timestamp.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.

            Returns:
            plotly.graph_objs._figure.Figure: The updated availability over time chart figure.
            """
            _options, var_info = callbacks.build_variable_options(
                self.global_semantic_map_data, _present_classes(descriptive_data))
            selected_classes = callbacks.resolve_variable_selection(variable_selection, var_info)
            # the over-time chart shows one variable at a time; a category or
            # empty selection falls back to the overall sample size
            variable_class = next(iter(selected_classes)) if selected_classes and len(selected_classes) == 1 else None
            return callbacks.generate_sample_size_over_time_chart(
                descriptive_data, variable_class=variable_class, semantic_map_data=self.global_semantic_map_data)

        def _register_view_switch(prefix):
            """Register the toggle/select callbacks for a 'Select visualisation' pill."""
            @self.App.callback(
                Output(f'{prefix}-view-menu', 'hidden'),
                [Input(f'{prefix}-view-toggle', 'n_clicks')]
            )
            def _toggle_view_menu(n_clicks):
                return (n_clicks or 0) % 2 == 0

            @self.App.callback(
                [Output(f'{prefix}-view-store', 'data'),
                 Output(f'{prefix}-view-menu', 'hidden'),
                 Output(f'{prefix}-view-indicator', 'children'),
                 Output(f'{prefix}-view-bar', 'className'),
                 Output(f'{prefix}-view-pie', 'className')],
                [Input(f'{prefix}-view-bar', 'n_clicks'),
                 Input(f'{prefix}-view-pie', 'n_clicks')]
            )
            def _select_view(bar_clicks, pie_clicks):
                ctx = dash.callback_context
                view = 'bar'
                if ctx.triggered:
                    view = ctx.triggered[0]['prop_id'].split('.')[0].replace(f'{prefix}-view-', '')
                labels = {'bar': '(Bar chart)', 'pie': '(Pie chart)'}
                classes = {v: 'filter-option current' if v == view else 'filter-option' for v in ('bar', 'pie')}
                return view, True, labels[view], classes['bar'], classes['pie']

        _register_view_switch('completeness')
        _register_view_switch('plausibility')

        def _register_variable_dropdown(dropdown_id):
            """Populate a variable-selection dropdown (categories first, then variables)."""
            @self.App.callback(
                [Output(dropdown_id, 'options'), Output(dropdown_id, 'value')],
                [Input('store', 'data')]
            )
            def _update_variable_options(descriptive_data):
                latest_data = descriptive_data[max(descriptive_data.keys())]
                present = set()
                for org_data in latest_data.values():
                    categorical, numerical = callbacks._load_organization_stats(org_data)
                    present.update(categorical['variable'].unique())
                    present.update(numerical['variable'].unique())
                options, _var_info = callbacks.build_variable_options(self.global_semantic_map_data, present)
                return options, []

        _register_variable_dropdown('availability-variable-dropdown')
        _register_variable_dropdown('availability-over-time-variable-dropdown')
        _register_variable_dropdown('completeness-variable-dropdown')
        _register_variable_dropdown('plausibility-variable-dropdown')

        @self.App.callback(
            Output('exploration-subset-selection-checkboxes', 'options'),
            [Input('store', 'data')]
        )
        def update_exploration_checkboxes(descriptive_data):
            """
            Callback function to populate the organisation selection checkboxes on
            the data exploration page with the organisations of the latest snapshot.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.

            Returns:
            list: A list of dictionaries representing the checkbox options.
            """
            latest_data = descriptive_data[max(descriptive_data.keys())]
            return [{'label': org, 'value': org} for org in sorted(latest_data.keys())]

        @self.App.callback(
            [Output('exploration-categorical-variable', 'options'),
             Output('exploration-categorical-variable', 'value')],
            [Input('store', 'data')]
        )
        def update_exploration_categorical_variables(descriptive_data):
            """
            Callback function to populate the categorical variable dropdown on the data
            exploration page. Offers every schema categorical variable present in the
            latest snapshot, plus a 'cancer_groups' option when ICD-10 coded variables
            are detected.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.

            Returns:
            list: The dropdown options with schema-based labels.
            str: The initially selected variable.
            """
            latest_data = descriptive_data[max(descriptive_data.keys())]
            present = set()
            for org_data in latest_data.values():
                categorical, _ = callbacks._load_organization_stats(org_data)
                present.update(categorical['variable'].unique())

            schema = self.global_semantic_map_data.get('schema', {})
            variables = schema.get('variables', {})
            options = []
            for var_name, var_data in sorted(variables.items()):
                if var_data.get('dataType') != 'categorical':
                    continue
                var_class = var_data.get('class', var_name)
                if var_class in present or var_name in present:
                    options.append({
                        'label': callbacks._readable_variable_name(var_class, self.global_semantic_map_data),
                        'value': var_name,
                    })
            if callbacks.detect_icd10_variables_in_data(descriptive_data):
                options.append({'label': 'Grouped cancer types (ICD-10 blocks)',
                                'value': callbacks.CANCER_GROUPS_VARIABLE})
            # no default selection: the dropdown shows its 'Categorical variable'
            # placeholder until the user picks a variable
            return options, None

        @self.App.callback(
            Output('exploration-view-menu', 'hidden'),
            [Input('exploration-view-toggle', 'n_clicks')]
        )
        def toggle_exploration_view_menu(n_clicks):
            """Open/close the 'Select visualisation' menu when the pill button is clicked."""
            return (n_clicks or 0) % 2 == 0

        @self.App.callback(
            [Output('exploration-view-store', 'data'),
             Output('exploration-view-menu', 'hidden'),
             Output('exploration-view-indicator', 'children'),
             Output('exploration-view-pie', 'className'),
             Output('exploration-view-bar', 'className'),
             Output('exploration-view-csv', 'className')],
            [Input('exploration-view-pie', 'n_clicks'),
             Input('exploration-view-bar', 'n_clicks'),
             Input('exploration-view-csv', 'n_clicks')]
        )
        def select_exploration_view(pie_clicks, bar_clicks, csv_clicks):
            """
            Store the chosen visualisation view, close the menu, update the current-view
            indicator on the pill button and mark the chosen menu option as current.
            """
            ctx = dash.callback_context
            view = 'pie'
            if ctx.triggered:
                view = ctx.triggered[0]['prop_id'].split('.')[0].replace('exploration-view-', '')
            labels = {'pie': '(Pie chart)', 'bar': '(Bar chart)', 'csv': '(CSV)'}
            classes = {v: 'filter-option current' if v == view else 'filter-option'
                       for v in ('pie', 'bar', 'csv')}
            return view, True, labels[view], classes['pie'], classes['bar'], classes['csv']

        @self.App.callback(
            [Output('exploration-categorical-graph', 'figure'),
             Output('exploration-categorical-graph', 'style'),
             Output('exploration-categorical-csv', 'hidden'),
             Output('exploration-categorical-csv-table', 'data'),
             Output('exploration-csv-store', 'data')],
            [Input('store', 'data'),
             Input('exploration-subset-selection-checkboxes', 'value'),
             Input('exploration-categorical-variable', 'value'),
             Input('exploration-view-store', 'data')]
        )
        def update_exploration_categorical_chart(descriptive_data, selection, variable, view):
            """
            Callback function to update the categorical chart on the data exploration
            page. Depending on the view it renders a pie chart, a bar chart, or the
            underlying counts as a CSV table (with a downloadable CSV in the store).
            Counts are summed over the selected organisations.

            Parameters:
            descriptive_data (dict): The data stored in the 'store' component.
            selection (list): The selected organisations.
            variable (str): The selected categorical variable ('cancer_groups' for the
                            ICD-10 binned cancer types).
            view (str): 'pie', 'bar' or 'csv'.

            Returns:
            plotly.graph_objs._figure.Figure: The chart figure.
            dict: The graph style (hidden in CSV view).
            bool: Whether the CSV view is hidden.
            list: The CSV table rows.
            str: The CSV text for download.
            """
            if view == 'bar':
                figure = callbacks.generate_categorical_bar_figure(
                    descriptive_data, selection, variable, self.global_semantic_map_data)
            else:
                figure = callbacks.generate_categorical_pie_figure(
                    descriptive_data, selection, variable, self.global_semantic_map_data)

            counts = callbacks.categorical_value_counts(
                descriptive_data, selection, variable, self.global_semantic_map_data)
            if counts is None:
                table_data, csv_text = [], ''
            else:
                labels, values = counts
                table_data = [{'category': label, 'count': value} for label, value in zip(labels, values)]
                csv_text = callbacks.format_categorical_csv(labels, values)

            return (figure,
                    {'display': 'none'} if view == 'csv' else {},
                    view != 'csv',
                    table_data,
                    csv_text)

        @self.App.callback(
            Output('exploration-csv-download', 'data'),
            [Input('exploration-csv-download-btn', 'n_clicks')],
            [State('exploration-csv-store', 'data')]
        )
        def download_exploration_csv(n_clicks, csv_text):
            """
            Callback function to download the currently shown categorical counts as CSV.

            Parameters:
            n_clicks (int): The download button click count.
            csv_text (str): The CSV text stored by the chart callback.

            Returns:
            dict: The dcc.Download data payload.
            """
            if not n_clicks or not csv_text:
                return dash.no_update
            return dcc.send_string(csv_text, 'categorical-variable-counts.csv')

        @self.App.callback(
            [Output('exploration-variable-dropdown', 'options'),
             Output('exploration-variable-dropdown', 'value')],
            [Input('aggregate-store', 'data')]
        )
        def update_exploration_variable_dropdown(aggregate_data):
            """
            Callback function to populate the variable dropdown on the data exploration
            page with the continuous variables of the latest central aggregate result.

            Parameters:
            aggregate_data (dict): The data stored in the 'aggregate-store' component.

            Returns:
            list: The dropdown options with schema-based labels.
            str: The initially selected variable.
            """
            _, numerical = callbacks.load_aggregate_stats(aggregate_data)
            variables = sorted(numerical['variable'].unique()) if not numerical.empty else []
            options = [{'label': callbacks._readable_variable_name(variable, self.global_semantic_map_data),
                        'value': variable} for variable in variables]
            # no default selection: the dropdown shows its 'Numerical variable'
            # placeholder and the graph stays empty until the user picks one
            return options, None

        @self.App.callback(
            [Output('exploration-distribution-graph', 'figure'),
             Output('exploration-distribution-stats', 'children')],
            [Input('aggregate-store', 'data'),
             Input('exploration-variable-dropdown', 'value')]
        )
        def update_exploration_distribution(aggregate_data, variable):
            """
            Callback function to update the distribution density curve on the data
            exploration page from the central aggregate (federated IQR) result, plus
            the one-line quartile summary shown next to the graph.

            Parameters:
            aggregate_data (dict): The data stored in the 'aggregate-store' component.
            variable (str): The selected variable's ontology class code.

            Returns:
            plotly.graph_objs._figure.Figure: The updated density curve figure.
            str: The quartile statistics summary line.
            """
            return (callbacks.generate_distribution_curve_figure(aggregate_data, variable,
                                                                 self.global_semantic_map_data),
                    callbacks.format_distribution_stats(aggregate_data, variable))

    def run(self, debug=None):
        """
        Start the Plotly Dash dashboard

        :param bool debug: specify whether to use debugging mode
        """
        if isinstance(debug, bool) is False:
            debug = False

        # Binding all interfaces is required inside the Docker container;
        # exposure to the host is controlled by the container's published port.
        self.App.run(debug=debug, dev_tools_ui=False, host='0.0.0.0')  # nosec B104


def main():
    schema_file_path = os.getenv('SCHEMA_FILE_PATH') or os.getenv('JSON_FILE_PATH')
    dashboard_data_file_path = os.getenv('DASHBOARD_DATA_FILE_PATH')

    dash_app = Dashboard(schema_file_path, dashboard_data_file_path)
    dash_app.run()


if __name__ == '__main__':
    main()
