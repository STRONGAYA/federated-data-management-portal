import copy
import io
import json
import math
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import simple_icd_10 as icd10

from collections import defaultdict
from dash import dash_table
from dash import html
from datetime import datetime

names_to_capitalise = ["eortc", "hads"]


def _finalize_figure(figure):
    """
    Disable the hover cross/anchor on a chart: no drag crosshair cursor
    (dragmode off) and no hover spikelines, on top of the template defaults.
    Accepts both go.Figure objects and plain dict figures.
    """
    if isinstance(figure, dict):
        layout = figure.setdefault('layout', {})
        layout['dragmode'] = False
        layout['hovermode'] = 'closest'
        return figure
    figure.update_layout(dragmode=False, hovermode='closest')
    figure.update_xaxes(showspikes=False)
    figure.update_yaxes(showspikes=False)
    return figure


def _load_stats_frame(raw_stats, expected_columns):
    """
    Load a JSON statistics string into a DataFrame with the expected columns.

    Missing, empty, or malformed statistics yield an empty DataFrame with the
    expected columns, so chart code can treat them as zero counts instead of
    raising a KeyError on a column that does not exist.

    Parameters:
    raw_stats (str): JSON string containing the statistics.
    expected_columns (list): Column names the chart code relies on.

    Returns:
    pd.DataFrame: The parsed statistics, or an empty DataFrame with the expected columns.
    """
    empty_frame = pd.DataFrame(columns=list(expected_columns))
    if not raw_stats:
        return empty_frame
    try:
        frame = pd.DataFrame(json.loads(raw_stats))
    except (json.JSONDecodeError, TypeError):
        return empty_frame
    if any(column not in frame.columns for column in expected_columns):
        return empty_frame
    return frame


def _load_organization_stats(org_data):
    """
    Load the categorical and numerical statistics of a single organisation.

    Accepts both the 'categorical'/'numerical' keys used by the dashboard data
    file and the vantage6-native 'categorical_general_partial_statistics'/
    'numerical_general_partial_statistics' keys, so raw task exports also work.

    Parameters:
    org_data (dict): The data of a single organisation.

    Returns:
    tuple: The (categorical, numerical) DataFrames, empty when no valid statistics are present.
    """
    categorical_key = 'categorical'
    if categorical_key not in org_data and 'categorical_general_partial_statistics' in org_data:
        categorical_key = 'categorical_general_partial_statistics'
    numerical_key = 'numerical'
    if numerical_key not in org_data and 'numerical_general_partial_statistics' in org_data:
        numerical_key = 'numerical_general_partial_statistics'

    categorical = _load_stats_frame(org_data.get(categorical_key), ['variable', 'value', 'count'])
    numerical = _load_stats_frame(org_data.get(numerical_key), ['variable', 'statistic', 'value'])

    # Rows without a variable identifier cannot be matched to the schema; drop
    # them so they neither crash the chart code nor inflate the counts.
    categorical = categorical.dropna(subset=['variable'])
    numerical = numerical.dropna(subset=['variable'])
    return categorical, numerical


def _safe_ratio(numerator, denominator):
    """
    Divide scalar counts, returning 0 when the denominator is zero.

    An organisation without any data points has no relative missing data, so
    its chart shows 0 instead of nan.

    Parameters:
    numerator (number): The numerator.
    denominator (number): The denominator.

    Returns:
    float: The ratio, or 0 when the denominator is zero.
    """
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _organisation_color_map(descriptive_data):
    """
    Assign every organisation a fixed colour from the active template colourway.

    The donut charts and the availability over time chart draw the same
    organisations; both look up their colours here, so an organisation keeps
    its colour across every chart on the page.

    Parameters:
    descriptive_data (dict): The descriptive data; every organisation in any
                             snapshot receives a colour.

    Returns:
    dict: Organisation name mapped to a colour from the template colourway.
    """
    organisations = sorted({org for snapshot in descriptive_data.values() for org in snapshot})
    colorway = pio.templates[pio.templates.default].layout.colorway
    return {org: colorway[i % len(colorway)] for i, org in enumerate(organisations)}


def _get_organization_sample_size(org_data):
    """
    Helper function to get the sample size for a single organization.
    
    Priority:
    1. Look for ncit:C164339 variable (explicit sample size variable)
    2. Use the highest count from numerical data (count statistic)
    3. Use the highest total count from categorical data (excluding nan)
    
    Parameters:
    org_data (dict): The organization data containing categorical and numerical statistics
    
    Returns:
    int: The calculated sample size for the organization
    """
    sample_size = 0

    # Get pre-set sample size
    _sample_size = org_data.get('sample_size', None)
    if _sample_size:
        sample_size = int(_sample_size)
        return sample_size

    # First, try to find ncit:C164339 variable (preferred sample size variable)
    target_variable = "ncit:C164339"
    found_target = False
    
    # Check categorical data for ncit:C164339
    # Check for new format first, then fall back to old format
    categorical_key = None
    if 'categorical_general_partial_statistics' in org_data:
        categorical_key = 'categorical_general_partial_statistics'
    elif 'categorical' in org_data:
        categorical_key = 'categorical'
    
    if categorical_key:
        try:
            categorical_df = pd.DataFrame(json.loads(org_data[categorical_key]))
            target_data = categorical_df[
                (categorical_df['variable'] == target_variable) & 
                (categorical_df['value'] != 'nan')
            ]
            if not target_data.empty:
                sample_size = target_data['count'].sum()
                found_target = True
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Check numerical data for ncit:C164339 if not found in categorical
    if not found_target:
        # Check for new format first, then fall back to old format
        numerical_key = None
        if 'numerical_general_partial_statistics' in org_data:
            numerical_key = 'numerical_general_partial_statistics'
        elif 'numerical' in org_data:
            numerical_key = 'numerical'
        
        if numerical_key:
            try:
                numerical_df = pd.DataFrame(json.loads(org_data[numerical_key]))
                target_data = numerical_df[
                    (numerical_df['variable'] == target_variable) & 
                    (numerical_df['statistic'] == 'count')
                ]
                if not target_data.empty:
                    sample_size = target_data['value'].sum()
                    found_target = True
            except (json.JSONDecodeError, KeyError):
                pass
    
    # If ncit:C164339 not found, use highest count from numerical data first
    if not found_target:
        max_count = 0
        
        # Check numerical data for highest count (preferred fallback)
        # Check for new format first, then fall back to old format
        numerical_key = None
        if 'numerical_general_partial_statistics' in org_data:
            numerical_key = 'numerical_general_partial_statistics'
        elif 'numerical' in org_data:
            numerical_key = 'numerical'
        
        if numerical_key:
            try:
                numerical_df = pd.DataFrame(json.loads(org_data[numerical_key]))
                for variable in numerical_df['variable'].unique():
                    var_data = numerical_df[
                        (numerical_df['variable'] == variable) & 
                        (numerical_df['statistic'] == 'count')
                    ]
                    if not var_data.empty:
                        var_count = var_data['value'].sum()
                        max_count = max(max_count, var_count)
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Check categorical data for highest count (last fallback)
        if max_count == 0:
            # Check for new format first, then fall back to old format
            categorical_key = None
            if 'categorical_general_partial_statistics' in org_data:
                categorical_key = 'categorical_general_partial_statistics'
            elif 'categorical' in org_data:
                categorical_key = 'categorical'
            
            if categorical_key:
                try:
                    categorical_df = pd.DataFrame(json.loads(org_data[categorical_key]))
                    for variable in categorical_df['variable'].unique():
                        var_data = categorical_df[
                            (categorical_df['variable'] == variable) & 
                            (categorical_df['value'] != 'nan')
                        ]
                        var_count = var_data['count'].sum()
                    max_count = max(max_count, var_count)
                except (json.JSONDecodeError, KeyError):
                    pass
        
        sample_size = max_count
    
    return int(sample_size)


def fetch_field_count(descriptive_data, field_name="country", text='countr'):
    """
    Function to fetch the count of unique fields from the descriptive data.

    This function takes in a dictionary of descriptive data, finds the latest data entry based on the keys
    (assumed to be timestamps), and returns a list containing the count of unique fields in the latest data, a line break,
    and the provided text (default is "countr") with 'ies' added if the count is more than 1, else 'y' is added.

    Parameters:
    descriptive_data (dict): The descriptive data to fetch the count of unique fields from. Each key is a timestamp,
                             and each value is a dictionary containing the data fetched at that timestamp.
    field_name (str, optional): The field name to count unique values for. Defaults to "country".
    text (str, optional): The text to return along with the count of unique fields. Defaults to "countr".

    Returns:
    list: A list containing the count of unique fields in the latest data, a line break, and the provided text with 'ies'
          added if the count is more than 1, else 'y' is added.
    """
    if descriptive_data:
        latest_data = descriptive_data[max(descriptive_data.keys())]
        num_countries = len({data[f"{field_name}"] for data in latest_data.values()})
        return [f"{num_countries}", html.Br(), f"{text}{'ies' if num_countries > 1 else 'y'}"]


def fetch_number_of_keys(descriptive_data, text='organisation'):
    """
    Function to fetch the number of keys from the descriptive data.

    This function takes in a dictionary of descriptive data, finds the latest data entry based on the keys
    (assumed to be timestamps), and returns a list containing the number of keys in the latest data, a line break,
    and the provided text (default is "organisation") with an 's' added if the number of keys is more than 1.

    Parameters:
    descriptive_data (dict): The descriptive data to fetch the number of keys from. Each key is a timestamp,
                             and each value is a dictionary containing the data fetched at that timestamp.
    text (str, optional): The text to return along with the number of keys. Defaults to "organisation".

    Returns:
    list: A list containing the number of keys in the latest data, a line break, and the provided text with an 's'
          added if the number of keys is more than 1.
    """
    if descriptive_data:
        latest_data = descriptive_data[max(descriptive_data.keys())]
        return [f"{len(latest_data)}", html.Br(), f"{text}{'s' if len(latest_data) > 1 else ''}"]


def fetch_total_sample_size(descriptive_data, text="AYA"):
    """
    Function to fetch the total sample size from the descriptive data.

    This function takes in a dictionary of descriptive data,
    finds the latest data entry based on the keys (assumed to be timestamps),
    and calculates the sample size using categorical and numerical statistics.
    Priority: 1) ncit:C164339 variable, 2) highest count from numerical data, 3) highest count from categorical data.
    It then returns a list containing the total sample size, a line break,
    and the provided text (default is "AYA") with an 's' added if the total sample size is more than 1.

    Parameters:
    descriptive_data (dict): The descriptive data to fetch the sample size from. Each key is a timestamp,
    and each value is a dictionary containing the data fetched at that timestamp.
    text (str, optional): The text to return along with the total sample size. Defaults to "AYA".

    Returns:
    list: A list containing the total sample size, a line break, and the provided text with an 's' added
            if the total sample size is more than 1.
    """
    if descriptive_data:
        latest_data = descriptive_data[max(descriptive_data.keys())]
        total_sample_size = 0
        
        for data in latest_data.values():
            sample_size = _get_organization_sample_size(data)
            total_sample_size += sample_size
            
        return [f"{total_sample_size}", html.Br(), f"{text}{'s' if total_sample_size > 1 else ''}"]


def filter_descriptive_data_by_prefix(descriptive_data, selected_prefixes):
    """
    Filter descriptive data to only include variables that start with the selected prefixes.

    Parameters:
    descriptive_data (dict): Dictionary containing the descriptive data with timestamps as keys
    selected_prefixes (list): List of prefix strings to filter variables by

    Returns:
    dict: Filtered descriptive data containing only variables with matching prefixes
    """
    if not descriptive_data or not selected_prefixes:
        return descriptive_data

    filtered_data = {}

    for timestamp, data in descriptive_data.items():
        filtered_data[timestamp] = {}

        for org, org_data in data.items():
            filtered_data[timestamp][org] = org_data.copy()

            # Filter categorical data
            # Check for new format first, then fall back to old format
            categorical_key = None
            if 'categorical_general_partial_statistics' in org_data:
                categorical_key = 'categorical_general_partial_statistics'
            elif 'categorical' in org_data:
                categorical_key = 'categorical'
            
            if categorical_key:
                categorical_df = pd.DataFrame(json.loads(org_data[categorical_key]))
                mask = categorical_df['variable'].apply(
                    lambda x: any(x.startswith(prefix) for prefix in selected_prefixes)
                )
                filtered_categorical = categorical_df[mask]
                filtered_data[timestamp][org]['categorical'] = filtered_categorical.to_json()

            # Filter numerical data
            # Check for new format first, then fall back to old format
            numerical_key = None
            if 'numerical_general_partial_statistics' in org_data:
                numerical_key = 'numerical_general_partial_statistics'
            elif 'numerical' in org_data:
                numerical_key = 'numerical'
            
            if numerical_key:
                numerical_df = pd.DataFrame(json.loads(org_data[numerical_key]))
                mask = numerical_df['variable'].apply(
                    lambda x: any(x.startswith(prefix) for prefix in selected_prefixes)
                )
                filtered_numerical = numerical_df[mask]
                filtered_data[timestamp][org]['numerical'] = filtered_numerical.to_json()

    return filtered_data


def filter_descriptive_data_by_semantic_map_categories(descriptive_data, selected_categories, semantic_map_data, max_depth=0):
    """
    Filter descriptive data to only include variables that belong to the selected semantic_map categories.

    Parameters:
    descriptive_data (dict): Dictionary containing the descriptive data with timestamps as keys
    selected_categories (list): List of category strings to filter variables by (e.g., ['demographic', 'clinical'])
    semantic_map_data (dict): Semantic_map data containing schema.variables with schemaReconstruction
    max_depth (int): Maximum depth to check in schemaReconstruction

    Returns:
    dict: Filtered descriptive data containing only variables with matching categories
    """
    selected_variable_classes = set()

    if not descriptive_data or not selected_categories or not semantic_map_data:
        return descriptive_data, selected_variable_classes

    # Create mapping from category values to aesthetic labels
    category_mapping = {}
    for cat in selected_categories:
        # Convert back from value format to aesthetic label with proper spacing
        # Remove leading underscore and capitalize properly
        category_mapping[cat] = cat.lstrip('_').replace('_', ' ').title()

    # Get variable classes (not names) that belong to selected categories
    schema = semantic_map_data.get('schema', {})
    variables = schema.get('variables', {})
    if variables:
        for variable_name, variable_data in variables.items():
            if 'schemaReconstruction' in variable_data and variable_data['schemaReconstruction']:
                # Check each level in schemaReconstruction up to max_depth
                # Only look at ClassNode items (not UnitNodes) within the specified depth
                for level, reconstruction_item in enumerate(variable_data['schemaReconstruction']):
                    if level >= max_depth:
                        break
                    
                    if (reconstruction_item.get('@type') == 'schema:ClassNode' and 
                        'aestheticLabel' in reconstruction_item and
                        reconstruction_item.get('placement') != 'before'):
                        # Remove underscores from aesthetic label and normalize
                        aesthetic_label = reconstruction_item['aestheticLabel'].replace('_', ' ')
                        # Check if this variable belongs to any selected category
                        for cat_value, cat_label in category_mapping.items():
                            if aesthetic_label.lower() == cat_label.lower():
                                # Add the class code instead of variable name
                                variable_class = variable_data.get('class')
                                if variable_class:
                                    selected_variable_classes.add(variable_class)
                                break

    if not selected_variable_classes:
        return descriptive_data, selected_variable_classes

    filtered_data = {}

    for timestamp, data in descriptive_data.items():
        filtered_data[timestamp] = {}

        for org, org_data in data.items():
            filtered_data[timestamp][org] = org_data.copy()

            # Filter categorical data
            # Check for new format first, then fall back to old format
            categorical_key = None
            if 'categorical_general_partial_statistics' in org_data:
                categorical_key = 'categorical_general_partial_statistics'
            elif 'categorical' in org_data:
                categorical_key = 'categorical'
            
            if categorical_key:
                categorical_df = pd.DataFrame(json.loads(org_data[categorical_key]))
                mask = categorical_df['variable'].isin(selected_variable_classes)
                filtered_categorical = categorical_df[mask]
                filtered_data[timestamp][org]['categorical'] = filtered_categorical.to_json()

            # Filter numerical data
            # Check for new format first, then fall back to old format
            numerical_key = None
            if 'numerical_general_partial_statistics' in org_data:
                numerical_key = 'numerical_general_partial_statistics'
            elif 'numerical' in org_data:
                numerical_key = 'numerical'
            
            if numerical_key:
                numerical_df = pd.DataFrame(json.loads(org_data[numerical_key]))
                mask = numerical_df['variable'].isin(selected_variable_classes)
                filtered_numerical = numerical_df[mask]
                filtered_data[timestamp][org]['numerical'] = filtered_numerical.to_json()


    return filtered_data, selected_variable_classes


def generate_sample_size_over_time_chart(descriptive_data, text="AYA"):
    """
    Generate a stacked bar chart of available sample sizes over time.

    Each snapshot timestamp contributes one bar on the horizontal axis. The bars
    stack the sample sizes of the individual organisations, so the height of a bar
    is the total number of available data points at that moment and the width of
    each segment is one organisation's contribution. Bars are used on purpose:
    a snapshot is an isolated measurement and nothing is known about the data
    between two snapshots, so the chart must not suggest a gradual change
    between them the way a line or area chart would.

    Parameters:
    descriptive_data (dict): The descriptive data to generate the chart from. Each key is a timestamp,
                             and each value is a dictionary containing the data fetched at that timestamp.
    text (str, optional): The text to use in the chart title and hovertemplate. Defaults to "AYA".

    Returns:
    go.Figure: The figure for the chart, or an annotation figure when no data is available.
    """
    if not descriptive_data:
        figure = go.Figure()
        figure.update_layout(
            annotations=[dict(
                text=f'No {text} data available',
                font=dict(family='Poppins, sans-serif', size=20),
                showarrow=False,
                x=0.5, y=0.5, xref='paper', yref='paper',
                xanchor='center', yanchor='middle',
            )],
            font=dict(family='Poppins, sans-serif'),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=400,
        )
        return _finalize_figure(figure)

    timestamps = sorted(descriptive_data.keys())
    organisations = sorted({org for snapshot in descriptive_data.values() for org in snapshot})

    dates = [datetime.fromisoformat(timestamp) for timestamp in timestamps]

    figure = go.Figure()
    organisation_colors = _organisation_color_map(descriptive_data)
    for org in organisations:
        sizes = [
            _get_organization_sample_size(descriptive_data[timestamp][org])
            if org in descriptive_data[timestamp] else 0
            for timestamp in timestamps
        ]
        figure.add_trace(go.Bar(
            x=dates,
            y=sizes,
            name=org,
            marker=dict(color=organisation_colors[org]),
            hovertemplate=(f"<b>{org}</b><br>"
                           f"%{{x|%d %B %Y}}: <b>%{{y:,}}</b> {text}{'s' if text[-1:] != 's' else ''}<extra></extra>"),
        ))

    # Annotate the total above each bar so the headline numbers are readable at a glance.
    totals = [0] * len(timestamps)
    for timestamp_index, timestamp in enumerate(timestamps):
        for org in descriptive_data[timestamp]:
            totals[timestamp_index] += _get_organization_sample_size(descriptive_data[timestamp][org])
    figure.update_layout(
        annotations=[
            dict(
                text=f'{total:,}',
                font=dict(family='Poppins, sans-serif', size=13, color='#484848'),
                showarrow=False,
                x=date, y=total, xref='x', yref='y',
                xanchor='center', yanchor='bottom', yshift=8,
            )
            for date, total in zip(dates, totals)
        ],
        title=f'Available {text} data points over time',
        hoverlabel=dict(font_family='Poppins, sans-serif'),
        font=dict(family='Poppins, sans-serif'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        barmode='stack',
        bargap=0.6,
        height=400,
        margin=dict(l=60, r=20, t=60, b=20),
        yaxis=dict(title=f'Number of {text} data points', rangemode='tozero'),
        xaxis=dict(title=None, tickformat='%d %b %Y'),
        legend=dict(orientation='h', yanchor='bottom', y=-0.35, xanchor='center', x=0.5),
    )

    return _finalize_figure(figure)


def generate_sample_size_horizontal_bar(descriptive_data, text="AYA"):
    """
    Function to generate a horizontal bar chart of sample sizes per organisation.

    This function takes in a dictionary of descriptive data, finds the latest data entry based on the keys
    (assumed to be timestamps), and generates a horizontal bar chart showing the sample sizes per organisation.
    The bar chart includes annotations showing the sample size for each organisation and
    the proportion of the total sample size that this represents.

    Parameters:
    descriptive_data (dict): The descriptive data to generate the bar chart from. Each key is a timestamp,
                             and each value is a dictionary containing the data fetched at that timestamp.
    text (str, optional): The text to use in the bar chart title and hovertemplate. Defaults to "AYA".

    Returns:
    dict: A dictionary representing the figure for the bar chart.
    This includes the data for the bars and the layout of the chart.
    """
    if descriptive_data:
        # Get the latest data
        latest_data = descriptive_data[max(descriptive_data.keys())]

        # Calculate the sample sizes using the consistent approach
        sample_sizes = []
        organisations = sorted(latest_data.keys())
        
        for org in organisations:
            sample_size = _get_organization_sample_size(latest_data[org])
            sample_sizes.append(sample_size)
        
        total_sample_size = sum(sample_sizes)
        proportions = [round((size / total_sample_size), ndigits=2) if total_sample_size > 0 else 0 for size in sample_sizes]

        # Create the data for the bar chart, keeping every organisation on the
        # colour it has in the donut charts and the availability over time chart.
        organisation_colors = _organisation_color_map(descriptive_data)
        data = [
            dict(
                x=[proportions[i]],
                y=[f'Number of {text}s per organisation'],
                name=org,
                type='bar',
                orientation='h',
                marker=dict(color=organisation_colors[org], line=dict(width=0)),
                hovertemplate=(
                    f"{org} has made data of {sample_sizes[i]} {text}{'s' if sample_sizes[i] > 1 else ''} available, "
                    f"which is {proportions[i] * 100:.2f}% of all available {text} data."
                )
            )
            for i, org in enumerate(organisations)
        ]

        # Create the annotations for the bar chart
        annotations = [
            dict(
                x=(sum(proportions[:i + 1]) - proportions[i] / 2),
                y=0,
                text=str(sample_sizes[i]),
                showarrow=False,
                font=dict(color='white')
            )
            for i in range(len(organisations))
        ]

        # Define the figure
        figure = {
            'data': data,
            'layout': {
                'title': f'Number of {text}s per organisation',
                'dragmode': False,
                'hovermode': 'closest',
                'barmode': 'stack',
                'plot_bgcolor': 'rgba(0,0,0,0)',
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'yaxis': {'visible': False},
                'xaxis': {
                    'tickformat': ',.0%',
                    'visible': False,
                },
                'legend': {
                    'orientation': 'h',
                    'traceorder': 'normal',
                    'yanchor': 'center',
                    'y': 0,
                    'xanchor': 'center',
                    'x': 0.48,
                },
                'height': 100,
                'margin': dict(l=45, r=0, t=35, b=25),
                'annotations': annotations
            }
        }
        return _finalize_figure(figure)


def generate_fair_data_availability(global_semantic_map_data, descriptive_data, text="AYA"):
    """
    Function to generate a DataFrame and a list of tooltips for FAIR data availability.

    This function takes in a dictionary of global semantic_map data, a dictionary of descriptive data, and a string text.
    It processes the data to generate a DataFrame and a list of tooltips, which are then used to create a Dash DataTable.
    Updated to use categorical and numerical statistics instead of variable_info for determining variable availability.

    Parameters:
    global_semantic_map_data (dict): The global semantic_map data to process. Each key is a variable name,
    and each value is a dictionary containing information about the variable.
    descriptive_data (dict): The descriptive data to process. Each key is a timestamp,
    and each value is a dictionary containing the data fetched at that timestamp.
    text (str, optional): The text to use in the tooltips. Defaults to "AYA".

    Returns:
    dash_table.DataTable: The created Dash DataTable.
    """
    df_rows = []
    tooltips = []   # Initialise tooltips as a list

    # prefixes for replacement purposes
    schema = global_semantic_map_data.get('schema', {})
    prefixes = dict(schema.get('prefixes', {}))
    if 'ncit' not in prefixes:
        prefixes['ncit'] = r'http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#'

    variable_info = schema.get('variables')
    if variable_info is None:
        variable_info = {}

    # Find the most recent timestamp
    most_recent_timestamp = max(descriptive_data.keys(), key=lambda x: datetime.fromisoformat(x))

    # Select the data associated with the most recent timestamp
    descriptive_data_most_recent = descriptive_data[most_recent_timestamp]

    # Get the list of organizations from the descriptive data
    organizations = list(descriptive_data_most_recent.keys())
    
    # Debug: Check if we have data in the expected format
    if organizations:
        sample_org = organizations[0]
        sample_data = descriptive_data_most_recent[sample_org]
        if 'categorical' in sample_data:
            try:
                cat_data = json.loads(sample_data['categorical'])
                if 'variable' in cat_data:
                    unique_vars = list(set(cat_data['variable'].values()))
                else:
                    pass
            except:
                pass
        if 'numerical' in sample_data:
            try:
                num_data = json.loads(sample_data['numerical'])
                if 'variable' in num_data:
                    unique_vars = list(set(num_data['variable'].values()))
                else:
                    pass
            except:
                pass

    _variable_info = copy.deepcopy(variable_info)


    # For each variable in the semantic map, create a row using categorical and numerical statistics
    for variable in variable_info.keys():
        org_variable_counts = {}
        variable_class = _variable_info[variable].get("class")

        for organisation in organizations:
            org_data = descriptive_data_most_recent[organisation]
            total_available = 0
            
            # Process categorical data for this variable
            # Check for new format first, then fall back to old format
            categorical_key = None
            if 'categorical_general_partial_statistics' in org_data:
                categorical_key = 'categorical_general_partial_statistics'
            elif 'categorical' in org_data:
                categorical_key = 'categorical'
            
            if categorical_key:
                try:

                    categorical_df = pd.DataFrame(json.loads(org_data[categorical_key]))

                    # Find rows for this variable (excluding nan values)
                    # The variable names should be already mapped from class codes in misc.py
                    var_data = categorical_df[
                        (categorical_df['variable'] == variable_class) &
                        (categorical_df['value'] != 'nan')
                    ]
                    cat_count = var_data['count'].sum()
                    total_available += cat_count
                except (json.JSONDecodeError, KeyError) as e:
                    pass
            
            # Process numerical data for this variable
            # Check for new format first, then fall back to old format
            numerical_key = None
            if 'numerical_general_partial_statistics' in org_data:
                numerical_key = 'numerical_general_partial_statistics'
            elif 'numerical' in org_data:
                numerical_key = 'numerical'
            
            if numerical_key:
                try:

                    numerical_df = pd.DataFrame(json.loads(org_data[numerical_key]))

                    # Find rows for this variable with 'count' statistic
                    var_data = numerical_df[
                        (numerical_df['variable'] == variable_class) &
                        (numerical_df['statistic'] == 'count')
                    ]
                    num_count = var_data['value'].sum()
                    total_available += num_count
                except (json.JSONDecodeError, KeyError) as e:
                    pass
            
            org_variable_counts[organisation] = int(total_available)

        # Compute the total count across all organizations
        total_count = sum(org_variable_counts.values())

        # ALL variables should appear in the table, regardless of count
        # Variables with zero count will show crosses, variables with data will show appropriate symbols

        row = {
            'Variables': variable.replace('_', ' ').upper() if
            any(name in variable for name in names_to_capitalise) else variable.replace('_', ' ').title(),
            f'Total {text}s': total_count,  # Include the total count in the row
        }

        # Create a tooltip row for each row - simplified to show only checkmarks/crosses
        org_data_list = []
        for org, count in org_variable_counts.items():
            has_data = count > 0
            org_data_list.append(f'{org}: ✓' if has_data else f'{org}: ✗')

        org_data = (
                       f'__{variable.replace("_", " ").upper() if any(name in variable for name in names_to_capitalise) else variable.replace("_", " ").title()}__  \n'
                       f'Availability per organisation  \n') + '  \n'.join(org_data_list)

        tooltip_row = {
            'Variables': f'__{variable.replace("_", " ").upper() if any(name in variable for name in names_to_capitalise) else variable.replace("_", " ").title()}__  \n'
                         f'Associated class: {variable_class}',
            f'Total {text}s': org_data
        }

        # Replace the full URI with a prefix in the tooltip
        for prefix, uri in prefixes.items():
            if uri in tooltip_row['Variables']:
                tooltip_row['Variables'] = tooltip_row['Variables'].replace(uri, prefix + ":")
                break

        # Add organization-specific data to the row and tooltip
        for organisation in organizations:
            count = org_variable_counts[organisation]
            
            # Check if any expected value classes are found for this organization
            any_expected_value_class_found = False
            
            # Check categorical data for expected value classes
            value_mapping = _variable_info[variable].get('valueMapping', {})
            
            # Determine if this variable should be subject to value class checking
            should_check_value_classes = False
            if value_mapping and value_mapping.get('terms') and count > 0:
                # Check if there are any terms other than 'missing_or_unspecified'
                non_missing_terms = [term for term in value_mapping.get('terms', {}).keys() 
                                   if term != 'missing_or_unspecified']
                should_check_value_classes = len(non_missing_terms) > 0
            
            if should_check_value_classes:
                org_data = descriptive_data_most_recent[organisation]
                # Check for new format first, then fall back to old format
                categorical_key = None
                if 'categorical_general_partial_statistics' in org_data:
                    categorical_key = 'categorical_general_partial_statistics'
                elif 'categorical' in org_data:
                    categorical_key = 'categorical'
                
                if categorical_key:
                    try:
                        categorical_df = pd.DataFrame(json.loads(org_data[categorical_key]))
                        actual_values = categorical_df[
                            categorical_df['variable'] == variable_class
                        ]['value'].unique()
                        
                        # Check each expected value class
                        for term_key, value_info in value_mapping.get('terms', {}).items():
                            if term_key == 'missing_or_unspecified':
                                continue
                                
                            target_class = value_info.get('targetClass', '')
                            
                            # Check if this target class is present
                            if target_class in actual_values:
                                any_expected_value_class_found = True
                                break
                            else:
                                # Check for full URI version
                                expanded_target_class = target_class
                                for prefix, uri in prefixes.items():
                                    if prefix + ":" in expanded_target_class:
                                        expanded_target_class = expanded_target_class.replace(prefix + ":", uri)
                                        break
                                
                                if expanded_target_class in actual_values:
                                    any_expected_value_class_found = True
                                    break
                    except (json.JSONDecodeError, KeyError):
                        pass
            
            # Store the count and the status for later symbol determination
            row[organisation] = count
            # Store additional info for symbol logic: (count, has_expected_classes, should_check_classes)
            row[f'{organisation}_status'] = (count, any_expected_value_class_found, should_check_value_classes)
            
            # Build tooltip with availability information
            main_status = '✓' if count > 0 else '✗'
            main_text = "available" if count > 0 else "unavailable"
            tooltip_text = f'{main_status} Data for __{variable.replace("_", " ")}__ {main_text} in {organisation}.'
            
            if count > 0:
                tooltip_text += f'  \nTotal records: {count}'
            
            # Add value mapping concepts if they exist (keep existing tooltip logic unchanged)
            if value_mapping and value_mapping.get('terms') and count > 0:
                tooltip_text += f'  \n  \nDetected value concepts:'
                org_data = descriptive_data_most_recent[organisation]
                
                # Check categorical data for value mappings
                # Check for new format first, then fall back to old format
                categorical_key = None
                if 'categorical_general_partial_statistics' in org_data:
                    categorical_key = 'categorical_general_partial_statistics'
                elif 'categorical' in org_data:
                    categorical_key = 'categorical'
                
                if categorical_key:
                    try:
                        categorical_df = pd.DataFrame(json.loads(org_data[categorical_key]))
                        # Get all actual values in the data for this variable
                        actual_values = categorical_df[
                            categorical_df['variable'] == variable_class
                        ]['value'].unique()
                        
                        # Check if the variable itself exists in the data
                        variable_exists = len(actual_values) > 0
                        
                        # Check each value mapping term to see if its target class is directly present
                        for term_key, value_info in value_mapping.get('terms', {}).items():
                            if term_key == 'missing_or_unspecified':
                                continue
                                
                            target_class = value_info.get('targetClass', '')
                            
                            # Check if the target class ontology code is directly present in the data
                            # Look for both prefixed (ncit:C20197) and full URI versions
                            target_class_found = False
                            
                            # Check for prefixed version (e.g., ncit:C20197)
                            if target_class in actual_values:
                                target_class_found = True
                            else:
                                # Check for full URI version by expanding prefixes
                                expanded_target_class = target_class
                                for prefix, uri in prefixes.items():
                                    if prefix + ":" in expanded_target_class:
                                        expanded_target_class = expanded_target_class.replace(prefix + ":", uri)
                                        break
                                
                                if expanded_target_class in actual_values:
                                    target_class_found = True
                            
                            # Determine the status symbol (keep existing tooltip logic - no warning symbol here)
                            if target_class_found:
                                value_status = '✓'  # Target class is present
                            elif variable_exists:
                                value_status = '✗'  # Variable exists but this target class not found
                            else:
                                value_status = '✗'  # Variable doesn't exist at all
                            
                            # Display the target class (ontology code) with prefix for readability
                            display_target = target_class
                            tooltip_text += f'  \n{value_status} {term_key.replace("_", " ").title()} ({display_target})'
                            
                    except (json.JSONDecodeError, KeyError):
                        pass
            
            tooltip_row[organisation] = tooltip_text

        # Append the row and tooltip row to the list of rows and tooltips
        df_rows.append(row)
        tooltips.append(tooltip_row)

    # Convert the list of rows to a DataFrame
    df = pd.DataFrame(df_rows)

    # Create a new DataFrame for display purposes with enhanced symbol logic
    display_df = df.copy()

    # Extract organization columns (skip 'Variables' and 'Total {text}s' columns)
    org_columns = [col for col in display_df.columns[2:] if not col.endswith('_status')]

    for col in org_columns:
        status_col = f'{col}_status'
        if status_col in display_df.columns:
            # Apply the enhanced symbol logic
            def get_symbol(row):
                count, has_expected_classes, should_check_classes = row[status_col]
                if count == 0:
                    return '✖'  # No data
                elif not should_check_classes:
                    return '✔'  # Has data and no value class checking needed (continuous variables, etc.)
                elif has_expected_classes:
                    return '✔'  # Has data and expected value classes found
                else:
                    return '!'  # Has data but no expected value classes found
            
            display_df[col] = display_df.apply(get_symbol, axis=1)
            # Remove the temporary status column
            display_df = display_df.drop(columns=[status_col])
        else:
            # Fallback to original logic for columns without status info
            display_df[col] = display_df[col].apply(lambda x: '✔' if x > 0 else '✖')

    return df, create_data_table(display_df, tooltips)


def create_data_table(df, tooltips):
    """
    Function to create a Dash DataTable.

    This function takes a pandas DataFrame and a list of tooltips as input, and returns a Dash DataTable.
    The DataTable includes several styles for the table, cells, data, and header,
    as well as conditional styles for the data.
    The tooltips are added to the DataTable based on the input list of tooltips.

    Parameters:
    df (pandas.DataFrame): The DataFrame to convert into a DataTable.
    tooltips (list): A list of tooltips to add to the DataTable.
    Each tooltip is a dictionary where the keys are column names and the values are the tooltip texts.

    Returns:
    dash_table.DataTable: The created Dash DataTable.
    """
    _style_table = {'height': '450px', 'overflowY': 'auto', 'max-width': '100%', 'width': '100%', 'overflowX': 'auto'}
    _style_cell = {
        'fontSize': '14px',
        'border': 'none',
        'padding': '0px 0px 0px 0px',
        'whiteSpace': 'normal',
        'textOverflow': 'ellipsis',
        'overflow': 'hidden'
    }
    _style_data = {'border': 'none'}
    _style_header = {'position': 'sticky', 'top': 0, 'backgroundColor': '#ffffff', 'fontWeight': 'bold',
                     'whiteSpace': 'normal'}

    data_table = dash_table.DataTable(
        id='table-data-availability',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        style_table=_style_table,
        style_cell=_style_cell,
        style_data=_style_data,
        style_header=_style_header,
        style_data_conditional=[
            {'if': {'column_id': col, 'filter_query': '{' + col + '} eq "' + symbol + '"'}, 'color': color}
            for col in df.columns[2:] for symbol, color in [('✔', 'green'), ('✖', 'red'), ('!', 'orange')]
        ],
        style_cell_conditional=[
            # Fixed columns require pixel widths; percentage widths are not
            # applied and leave the organisation columns far too wide.
            {'if': {'column_id': 'Variables'}, 'width': '160px'},
            {'if': {'column_id': 'Total AYAs'}, 'width': '70px'},
            *[
                # The organisation columns hold a single availability symbol;
                # the header text wraps vertically to keep the columns narrow.
                {'if': {'column_id': col}, 'width': '80px'}
                for col in df.columns[2:]
            ]
        ],
        tooltip_data=[
            {column: {'value': str(tooltip[column]), 'type': 'markdown'}
            if column in tooltip else None for column in df.columns}
            for tooltip in tooltips
        ],
        fixed_columns={'headers': True, 'data': 2},
        tooltip_duration=None,
        filter_action="native",
        sort_action="native",
        page_action="native",
    )
    return data_table


def generate_donut_chart(descriptive_data, text="AYA", chart_domain='availability', chart_type="organisation"):
    """
    Function to generate a donut chart of sample sizes per organisation or AYAs per country.

    This function takes in a dictionary of descriptive data, finds the latest data entry based on the keys
    (assumed to be timestamps), and generates a donut chart showing the sample sizes per organisation or AYAs per country.
    The donut chart includes annotations showing the sample size for each organisation or country and
    the proportion of the total sample size that this represents.

    Parameters:
    descriptive_data (dict): The descriptive data to generate the donut chart from. Each key is a timestamp,
                             and each value is a dictionary containing the data fetched at that timestamp.
    text (str, optional): The text to use in the donut chart title and hovertemplate. Defaults to "AYA".
    chart_type (str, optional): The type of chart to generate.
    Can be "organisation" or "country". Defaults to "organisation".

    Returns:
    dict: A dictionary representing the figure for the donut chart.
    This includes the data for the donut chart and the layout of the chart.
    """
    if descriptive_data:
        latest_data = descriptive_data[max(descriptive_data.keys())]

        if chart_domain == "availability":
            if chart_type == "organisation":
                labels = sorted(latest_data.keys())
                sample_sizes = []
                
                for org in labels:
                    sample_size = _get_organization_sample_size(latest_data[org])
                    sample_sizes.append(sample_size)
                
                title = f'{text}s per organisation'
            elif chart_type == "country":
                country_data = defaultdict(int)
                
                for data in latest_data.values():
                    sample_size = _get_organization_sample_size(data)
                    country_data[data["country"]] += sample_size
                
                labels, sample_sizes = zip(*sorted(country_data.items()))
                title = f'{text}s per country'
            _custom_data = None
            hover = f"<b>%{{label}}</b><br>Available {text} data: <b>%{{value}}</b><br>" \
                    f"Proportion of all available {text} data: <b>%{{percent}}</b>"
        elif chart_domain == "completeness":
            if chart_type == "organisation":
                labels = sorted(latest_data.keys())
                missing_counts = []
                _custom_data = []
                for org in labels:
                    data = latest_data[org]
                    categorical_data, numerical_data = _load_organization_stats(data)

                    # Calculate total counts excluding 'nan' and 'outliers'
                    total_categorical_count = categorical_data[categorical_data["value"] != "nan"]["count"].sum()
                    total_numerical_count = numerical_data[numerical_data["statistic"] == "count"]["value"].sum()

                    # Calculate missing counts
                    missing_categorical_count = categorical_data[categorical_data["value"] == "nan"]["count"].sum()
                    missing_numerical_count = numerical_data[numerical_data["statistic"] == "nan"]["value"].sum()

                    # Sum relative missing counts
                    relative_missing_count = _safe_ratio(
                        missing_categorical_count + missing_numerical_count,
                        (total_categorical_count + missing_categorical_count)
                        + (total_numerical_count + missing_numerical_count))
                    missing_counts.append(total_categorical_count + total_numerical_count)
                    _custom_data.append((round((relative_missing_count * 100), 1)))

                title = f'Complete {text} data points per organisation'
                sample_sizes = missing_counts
            elif chart_type == "country":
                country_data = defaultdict(float)
                relative_country_data = defaultdict(float)
                for data in latest_data.values():
                    categorical_data, numerical_data = _load_organization_stats(data)

                    # Calculate total counts excluding 'nan' and 'outliers'
                    total_categorical_count = categorical_data[categorical_data["value"] != "nan"]["count"].sum()
                    total_numerical_count = numerical_data[numerical_data["statistic"] == "count"]["value"].sum()

                    # Calculate missing counts
                    missing_categorical_count = categorical_data[categorical_data["value"] == "nan"]["count"].sum()
                    missing_numerical_count = numerical_data[numerical_data["statistic"] == "nan"]["value"].sum()

                    # Sum relative missing counts
                    relative_missing_count = _safe_ratio(
                        missing_categorical_count + missing_numerical_count,
                        (total_categorical_count + missing_categorical_count)
                        + (total_numerical_count + missing_numerical_count))
                    country_data[data["country"]] += (total_categorical_count + total_numerical_count)
                    relative_country_data[data["country"]] += round((relative_missing_count * 100), 1)

                labels, sample_sizes = zip(*sorted(country_data.items()))
                _custom_data = [relative_country_data[label] for label in labels]
                title = f'Complete {text} data points per country'
            hover = f"<b>%{{label}}</b><br>Relative incomplete data points: <b>%{{customdata}}%</b><br><br>" \
                    f"Complete {text} data points: <b>%{{value}}</b><br>" \
                    f"Proportion of all complete {text} data points: <b>%{{percent}}</b>"
            # Calculate plausible counts and relative plausible counts
        elif chart_domain == "plausibility":
            if chart_type == "organisation":
                labels = sorted(latest_data.keys())
                plausible_counts = []
                _custom_data = []
                for org in labels:
                    data = latest_data[org]
                    categorical_data, numerical_data = _load_organization_stats(data)

                    # Calculate total counts excluding 'outliers'
                    total_categorical_count = categorical_data["count"].sum()
                    total_numerical_count = numerical_data[numerical_data["statistic"] == "count"]["value"].sum()

                    # Calculate implausible counts
                    implausible_categorical_count = categorical_data[categorical_data["value"] == "outliers"][
                        "count"].sum()
                    implausible_numerical_count = numerical_data[numerical_data["statistic"] == "outliers"][
                        "value"].sum()

                    # Calculate plausible counts
                    plausible_categorical_count = total_categorical_count - implausible_categorical_count
                    plausible_numerical_count = total_numerical_count - implausible_numerical_count

                    # Calculate relative plausible counts
                    total_count = total_categorical_count + total_numerical_count
                    plausible_count = plausible_categorical_count + plausible_numerical_count
                    relative_plausible_count = plausible_count / total_count if total_count != 0 else 0

                    plausible_counts.append(plausible_count)
                    _custom_data.append(round((relative_plausible_count * 100), 1))

                title = f'Plausible {text} data points per organisation'
                sample_sizes = plausible_counts

            elif chart_type == "country":
                country_data = defaultdict(float)
                relative_country_data = defaultdict(float)
                for data in latest_data.values():
                    categorical_data, numerical_data = _load_organization_stats(data)

                    # Calculate total counts excluding 'outliers'
                    total_categorical_count = categorical_data["count"].sum()
                    total_numerical_count = numerical_data[numerical_data["statistic"] == "count"]["value"].sum()

                    # Calculate implausible counts
                    implausible_categorical_count = categorical_data[categorical_data["value"] == "outliers"][
                        "count"].sum()
                    implausible_numerical_count = numerical_data[numerical_data["statistic"] == "outliers"][
                        "value"].sum()

                    # Calculate plausible counts
                    plausible_categorical_count = total_categorical_count - implausible_categorical_count
                    plausible_numerical_count = total_numerical_count - implausible_numerical_count

                    # Calculate relative plausible counts
                    total_count = total_categorical_count + total_numerical_count
                    plausible_count = plausible_categorical_count + plausible_numerical_count
                    relative_plausible_count = plausible_count / total_count if total_count != 0 else 0

                    country_data[data["country"]] += plausible_count
                    relative_country_data[data["country"]] += round((relative_plausible_count * 100), 1)

                labels, sample_sizes = zip(*sorted(country_data.items()))
                _custom_data = [min(relative_country_data[label], 100) for label in labels]  # Ensure max 100%
            title = f'Plausible {text} data points per country'
            hover = f"<b>%{{label}}</b><br>Relative plausible data points: <b>%{{customdata}}%</b><br><br>" \
                    f"Plausible {text} data points: <b>%{{value}}</b><br>" \
                    f"Proportion of all plausible {text} data points: <b>%{{percent}}</b>"

        # Keep every organisation on the colour it has in the availability over
        # time chart; country charts keep plotly's default sector colours.
        if chart_type == "organisation":
            organisation_colors = _organisation_color_map(descriptive_data)
            sector_colors = [organisation_colors.get(label) for label in labels]
        else:
            sector_colors = None

        data = [
            dict(
                labels=labels,
                values=sample_sizes,
                type='pie',
                hole=.56,
                name='',
                hovertemplate=(hover),
                customdata=_custom_data,
                textinfo='value',
                marker=dict(colors=sector_colors)
            )
        ]

        figure = go.Figure(data=data)

        figure.update_layout(
            title=title,
            hoverlabel=dict(font_family='Poppins, sans-serif'),
            font=dict(family='Poppins, sans-serif'),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                orientation='h',
                yanchor='top',
                y=0,
                xanchor='center',
                x=0.5,
            ),
        )

        return _finalize_figure(figure)


def generate_variable_bar_chart(descriptive_data, domain='completeness', text="AYA", semantic_map_data=None):
    """
    Function to generate a bar chart for data completeness or plausibility.

    This function takes in a dictionary of descriptive data, calculates the completeness or plausibility of the data,
    and generates a bar chart showing the completeness or plausibility of the data.
    The chart includes annotations showing the completeness or plausibility for each organization and
    the proportion of the total completeness or plausibility that this represents.

    Parameters:
    descriptive_data (dict): The descriptive data to generate the chart from.
    domain (str, optional): The domain to generate the chart for. Can be 'completeness' or 'plausibility'. Defaults to 'completeness'.
    text (str, optional): The text to use in the chart title and hovertemplate. Defaults to "AYA".
    semantic_map_data (dict, optional): The semantic map data to convert ontology codes to human-readable names.

    Returns:
    dict: A dictionary representing the figure for the chart.
    This includes the data for the chart and the layout of the chart.
    """
    if descriptive_data:
        # Get the latest data entry based on the keys
        latest_data = descriptive_data[max(descriptive_data.keys())]
        
        # Helper function to convert ontology codes to human-readable names
        def get_readable_variable_name(ontology_code):
            schema = semantic_map_data.get('schema', {}) if semantic_map_data else {}
            variables = schema.get('variables', {})
            if variables:
                variable_info = variables
                # Expand prefixes in ontology code if needed
                expanded_code = ontology_code
                schema_prefixes = schema.get('prefixes', {})
                if schema_prefixes:
                    prefixes = dict(schema_prefixes)
                    if 'ncit' not in prefixes:
                        prefixes['ncit'] = r'http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#'
                    for prefix, uri in prefixes.items():
                        if prefix + ":" in expanded_code:
                            expanded_code = expanded_code.replace(prefix + ":", uri)
                            break
                
                # Find the variable key that matches this ontology code
                for var_key, var_data in variable_info.items():
                    var_class = var_data.get('class', '')
                    # Expand prefixes in variable class too
                    expanded_var_class = var_class
                    if schema_prefixes:
                        for prefix, uri in prefixes.items():
                            if prefix + ":" in expanded_var_class:
                                expanded_var_class = expanded_var_class.replace(prefix + ":", uri)
                                break
                    
                    if expanded_var_class == expanded_code or var_class == ontology_code:
                        # Return the human-readable variable key name
                        return var_key.replace('_', ' ').upper() if any(name in var_key for name in names_to_capitalise) else var_key.replace('_', ' ').title()
            
            # Fallback: use the ontology code with some formatting
            return ontology_code.replace('_', ' ').upper() if any(name in ontology_code for name in names_to_capitalise) else ontology_code.replace('_', ' ').title()

        if domain == 'completeness':
            # Initialize dictionaries to store total available and unavailable data points
            total_available = {}
            total_unavailable = {}
            completeness_info = {}

            # Get sorted list of organization labels
            labels = sorted(latest_data.keys())

            for org in labels:
                completeness_info[org] = {}
                data = latest_data[org]
                categorical_data, numerical_data = _load_organization_stats(data)

                # Process categorical data
                for var in categorical_data['variable'].unique():
                    missing_count = \
                        categorical_data[(categorical_data['variable'] == var) & (categorical_data['value'] == 'nan')][
                            'count'].sum()
                    total_count = \
                        categorical_data[(categorical_data['variable'] == var) & (categorical_data['value'] != 'nan')][
                            'count'].sum()
                    if var not in total_available:
                        total_available[var] = 0
                        total_unavailable[var] = 0

                    total_available[var] += total_count
                    total_unavailable[var] += missing_count

                    completeness_info[org].update({var: (total_count, missing_count)})

                # Process numerical data
                for var in numerical_data['variable'].unique():
                    missing_count = \
                        numerical_data[(numerical_data['variable'] == var) & (numerical_data['statistic'] == 'nan')][
                            'value'].sum()
                    total_count = \
                        numerical_data[(numerical_data['variable'] == var) & (numerical_data['statistic'] == 'count')][
                            'value'].sum()

                    if var not in total_available:
                        total_available[var] = 0
                        total_unavailable[var] = 0

                    total_available[var] += total_count
                    total_unavailable[var] += missing_count

                    completeness_info[org].update({var: (total_count, missing_count)})

            # Create DataFrame for visualization with human-readable variable names
            readable_variables = [get_readable_variable_name(var) for var in total_available.keys()]
            visualisation_df = pd.DataFrame({
                'Variables': readable_variables,
                f'Total available {text}s': list(total_available.values()),
                f'Total unavailable {text}s': list(total_unavailable.values())
            })
            # Keep a mapping of readable names to original codes for tooltip lookup
            var_name_mapping = dict(zip(readable_variables, total_available.keys()))

            # Calculate percentages; variables without any data points count as 0%
            totals = visualisation_df[f'Total available {text}s'] + visualisation_df[f'Total unavailable {text}s']
            nonzero_totals = totals.replace(0, np.nan)
            visualisation_df[f'Percentage available {text}s'] = (
                    visualisation_df[f'Total available {text}s'] / nonzero_totals).fillna(0)
            visualisation_df[f'Percentage unavailable {text}s'] = (
                    visualisation_df[f'Total unavailable {text}s'] / nonzero_totals).fillna(0)

            # Ensure minimum bar height
            min_bar_height = 0.01
            if visualisation_df[f'Percentage available {text}s'].min() != 0:
                visualisation_df[f'Percentage available {text}s'] = visualisation_df[
                    f'Percentage available {text}s'].apply(
                    lambda x: max(x, min_bar_height))
            if visualisation_df[f'Percentage unavailable {text}s'].min() != 0:
                visualisation_df[f'Percentage unavailable {text}s'] = visualisation_df[
                    f'Percentage unavailable {text}s'].apply(
                    lambda x: max(x, min_bar_height))

            # Set chart labels and hover templates for completeness
            yaxis_title = "Data point completeness"
            bar_name_available = "Complete data points"
            bar_name_unavailable = "Incomplete data points"
            pattern_shape = "\\"
            hovertemplate_available = [
                f"<extra></extra><b>{row['Variables']}</b><br>"
                f"Total complete data points: <b>{int(row[f'Total available {text}s'])}</b><br>"
                f"Percentage complete points: <b>{row[f'Percentage available {text}s'] * 100:.1f}%</b><br><br>"
                f"Share per organisation<br>" + "<br>".join(
                    f"{org}: <b>{completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[0]}</b> ({(completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[0] / (completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[0] + completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[1])) * 100:.1f}% complete data points)"
                    if (completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[0] +
                        completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[
                            1]) != 0 else f"{org} has no '{row['Variables']}' information available."
                    for org in labels
                )
                for index, row in visualisation_df.iterrows()
            ]
            hovertemplate_unavailable = [
                f"<extra></extra><b>{row['Variables']}</b><br>"
                f"Total incomplete data points: <b>{int(row[f'Total unavailable {text}s'])}</b><br>"
                f"Percentage incomplete data points: <b>{row[f'Percentage unavailable {text}s'] * 100:.1f}%</b><br><br>"
                f"Share per organisation<br>" + "<br>".join(
                    f"{org}: <b>{completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[1]}</b> ({(completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[1] / (completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[0] + completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[1])) * 100:.1f}% incomplete data points)"
                    if (completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[0] +
                        completeness_info[org].get(var_name_mapping[row['Variables']], (0, 0))[
                            1]) != 0 else f"{org} has no '{row['Variables']}' information available."
                    for org in labels
                )
                for index, row in visualisation_df.iterrows()
            ]

        elif domain == 'plausibility':
            # Initialize dictionaries to store total available and unavailable data points
            total_available = {}
            total_unavailable = {}
            completeness_info = {}

            # Get sorted list of organization labels
            labels = sorted(latest_data.keys())

            for org in labels:
                completeness_info[org] = {}
                data = latest_data[org]
                categorical_data, numerical_data = _load_organization_stats(data)

                # Process categorical data
                for var in categorical_data['variable'].unique():
                    implausible_count = \
                        categorical_data[
                            (categorical_data['variable'] == var) & (categorical_data['value'] == 'outliers')][
                            'count'].sum()
                    total_count = \
                        categorical_data[
                            (categorical_data['variable'] == var) & (categorical_data['value'] != 'outliers')][
                            'count'].sum()
                    if var not in total_available:
                        total_available[var] = 0
                        total_unavailable[var] = 0

                    total_available[var] += total_count
                    total_unavailable[var] += implausible_count

                    completeness_info[org].update({var: (total_count, implausible_count)})

                # Process numerical data
                for var in numerical_data['variable'].unique():
                    implausible_count = \
                        numerical_data[
                            (numerical_data['variable'] == var) & (numerical_data['statistic'] == 'outliers')][
                            'value'].sum()
                    total_count = \
                        numerical_data[(numerical_data['variable'] == var) & (numerical_data['statistic'] == 'count')][
                            'value'].sum() - implausible_count

                    if var not in total_available:
                        total_available[var] = 0
                        total_unavailable[var] = 0

                    total_available[var] += total_count
                    total_unavailable[var] += implausible_count

                    completeness_info[org].update({var: (total_count, implausible_count)})

            # Create DataFrame for visualization with human-readable variable names
            readable_variables = [get_readable_variable_name(var) for var in total_available.keys()]
            visualisation_df = pd.DataFrame({
                'Variables': readable_variables,
                f'Total available {text}s': list(total_available.values()),
                f'Total unavailable {text}s': list(total_unavailable.values())
            })
            # Keep a mapping of readable names to original codes for tooltip lookup
            var_name_mapping = dict(zip(readable_variables, total_available.keys()))

            # Calculate percentages; variables without any data points count as 0%
            totals = visualisation_df[f'Total available {text}s'] + visualisation_df[f'Total unavailable {text}s']
            nonzero_totals = totals.replace(0, np.nan)
            visualisation_df[f'Percentage available {text}s'] = (
                    visualisation_df[f'Total available {text}s'] / nonzero_totals).fillna(0)
            visualisation_df[f'Percentage unavailable {text}s'] = (
                    visualisation_df[f'Total unavailable {text}s'] / nonzero_totals).fillna(0)

            # Ensure minimum bar height
            min_bar_height = 0.01
            if visualisation_df[f'Percentage available {text}s'].min() != 0:
                visualisation_df[f'Percentage available {text}s'] = visualisation_df[
                    f'Percentage available {text}s'].apply(
                    lambda x: max(x, min_bar_height))
            if visualisation_df[f'Percentage unavailable {text}s'].min() != 0:
                visualisation_df[f'Percentage unavailable {text}s'] = visualisation_df[
                    f'Percentage unavailable {text}s'].apply(
                    lambda x: max(x, min_bar_height))

            # Set chart labels and hover templates for plausibility
            yaxis_title = "Data point plausibility"
            bar_name_available = "Plausible data points"
            bar_name_unavailable = "Implausible data points"
            pattern_shape = "/"
            hovertemplate_available = [
                f"<extra></extra><b>{row['Variables']}</b><br>"
                f"Total plausible data points: <b>{int(row[f'Total available {text}s'])}</b><br>"
                f"Percentage plausible data points: <b>{row[f'Percentage available {text}s'] * 100:.1f}%</b><br><br>"
                f"Share per organisation<br>" + "<br>".join(
                    f"{org}: <b>{completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[0]}</b> ({(completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[0] / (completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[0] + completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[1])) * 100:.1f}% plausible data points)"
                    if (completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[0] +
                        completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[1]) != 0
                    else f"{org} has no '{row['Variables']}' information available."
                    for org in labels
                )
                for index, row in visualisation_df.iterrows()
            ]

            hovertemplate_unavailable = [
                f"<extra></extra><b>{row['Variables']}</b><br>"
                f"Total implausible data points: <b>{int(row[f'Total unavailable {text}s'])}</b><br>"
                f"Percentage implausible: <b>{row[f'Percentage unavailable {text}s'] * 100:.1f}%</b><br><br>"
                f"Share per organisation<br>" + "<br>".join(
                    f"{org}: <b>{completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[1]}</b> ({(completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[1] / (completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[0] + completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[1])) * 100:.1f}% implausible data points)"
                    if (completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[0] +
                        completeness_info.get(org, {}).get(var_name_mapping[row['Variables']], (0, 0))[1]) != 0
                    else f"{org} has no '{row['Variables']}' information available."
                    for org in labels
                )
                for index, row in visualisation_df.iterrows()
            ]

        # Create the bar chart figure
        fig = go.Figure(data=[
            go.Bar(
                name=bar_name_available,
                x=visualisation_df['Variables'],
                y=visualisation_df[f'Percentage available {text}s'],
                width=0.4,
                hovertemplate=hovertemplate_available
            ),
            go.Bar(
                name=bar_name_unavailable,
                x=visualisation_df['Variables'],
                y=visualisation_df[f'Percentage unavailable {text}s'],
                width=0.4,
                hovertemplate=hovertemplate_unavailable,
                marker=dict(
                    pattern_shape=pattern_shape,
                    pattern_fillmode="replace",
                    pattern_solidity=0.3
                )
            )
        ])

        fig.update_layout(
            hoverlabel=dict(font_family='Poppins, sans-serif'),
            barmode='stack',
            font=dict(family='Poppins, sans-serif'),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=400,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(
                yanchor="top",
                y=-1.2,
                xanchor="center",
                x=0.5,
                orientation="h"
            ),
            yaxis_title=yaxis_title,
            yaxis=dict(tickformat=".0%"),
            xaxis=dict(
                tickangle=-45,
                rangeslider=dict(visible=True),
                range=[-0.5, 8.5]
            )
        )

        return _finalize_figure(fig)


def generate_variable_donut_chart(descriptive_data, domain='completeness', text="AYA", semantic_map_data=None):
    """
    Donut of the overall complete/incomplete (completeness) or plausible/implausible
    (plausibility) share, aggregated over all organisations and variables of the
    latest snapshot. Used as the alternative view of the variable bar charts.

    Returns:
    plotly.graph_objs._figure.Figure: The donut chart, or an annotation figure.
    """
    if not descriptive_data:
        return _finalize_figure(_empty_annotation_figure(f'No {text} data available'))
    latest_data = descriptive_data[max(descriptive_data.keys())]
    total_available = 0
    total_unavailable = 0
    for org in latest_data:
        categorical_data, numerical_data = _load_organization_stats(latest_data[org])
        if domain == 'completeness':
            total_available += categorical_data[categorical_data['value'] != 'nan']['count'].sum()
            total_available += numerical_data[numerical_data['statistic'] == 'count']['value'].sum()
            total_unavailable += categorical_data[categorical_data['value'] == 'nan']['count'].sum()
            total_unavailable += numerical_data[numerical_data['statistic'] == 'nan']['value'].sum()
        else:
            implausible_cat = categorical_data[categorical_data['value'] == 'outliers']['count'].sum()
            implausible_num = numerical_data[numerical_data['statistic'] == 'outliers']['value'].sum()
            total_available += categorical_data['count'].sum() - implausible_cat
            total_available += numerical_data[numerical_data['statistic'] == 'count']['value'].sum() - implausible_num
            total_unavailable += implausible_cat + implausible_num
    if domain == 'completeness':
        labels = [f'Complete {text} data points', f'Incomplete {text} data points']
    else:
        labels = [f'Plausible {text} data points', f'Implausible {text} data points']
    return _finalize_figure(_donut_figure(labels, [total_available, total_unavailable]))


def generate_unavailable_organisation_annotation(domain):
    """
    Generate a Plotly figure with a centered annotation.

    This function creates a Plotly figure that contains a centered annotation with a message
    indicating that the user should select an organisation to inspect variable data.
    The figure has no visible axes and a transparent background.

    Parameters:
    domain (str, optional): The domain to include in the annotation text.

    Returns:
    plotly.graph_objs._figure.Figure: A Plotly figure with the annotation.
    """
    fig = go.Figure().add_annotation(
        text=f"Select an organisation to visualise variable {domain}",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(family='Poppins, sans-serif', size=20),
        xanchor='center', yanchor='middle'
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return _finalize_figure(fig)


def _empty_annotation_figure(text):
    """
    Generate a Plotly figure with a single centered annotation and no axes.

    Parameters:
    text (str): The message to display.

    Returns:
    plotly.graph_objs._figure.Figure: The annotation figure.
    """
    figure = go.Figure()
    figure.update_layout(
        annotations=[dict(
            text=text,
            font=dict(family='Poppins, sans-serif', size=20),
            showarrow=False,
            x=0.5, y=0.5, xref='paper', yref='paper',
            xanchor='center', yanchor='middle',
        )],
        font=dict(family='Poppins, sans-serif'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=400,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return _finalize_figure(figure)


def _schema_prefixes(semantic_map_data):
    """Return the schema prefixes, always including the ncit prefix."""
    schema = semantic_map_data.get('schema', {}) if semantic_map_data else {}
    prefixes = dict(schema.get('prefixes', {}))
    if 'ncit' not in prefixes:
        prefixes['ncit'] = r'http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#'
    return prefixes


def _expand_prefix(code, prefixes):
    """Expand a prefixed ontology code (e.g. 'ncit:C28421') to its full URI."""
    if not isinstance(code, str):
        return code
    for prefix, uri in prefixes.items():
        if prefix + ':' in code:
            return code.replace(prefix + ':', uri, 1)
    return code


def _readable_variable_name(ontology_code, semantic_map_data=None):
    """
    Map an ontology class code to the human-readable schema variable name.

    Falls back to a formatted version of the code itself when the code is not
    part of the schema.
    """
    schema = semantic_map_data.get('schema', {}) if semantic_map_data else {}
    variables = schema.get('variables', {})
    prefixes = _schema_prefixes(semantic_map_data)
    expanded_code = _expand_prefix(ontology_code, prefixes)
    for var_key, var_data in variables.items():
        var_class = var_data.get('class', '')
        if var_class == ontology_code or _expand_prefix(var_class, prefixes) == expanded_code:
            return var_key.replace('_', ' ').upper() if any(
                name in var_key for name in names_to_capitalise) else var_key.replace('_', ' ').title()
    return ontology_code.replace('_', ' ').upper() if any(
        name in ontology_code for name in names_to_capitalise) else ontology_code.replace('_', ' ').title()


def _variable_class(variable_name, semantic_map_data=None):
    """Resolve a schema variable name to its ontology class code."""
    schema = semantic_map_data.get('schema', {}) if semantic_map_data else {}
    variables = schema.get('variables', {})
    if variable_name in variables:
        return variables[variable_name].get('class', variable_name)
    return variable_name


def _value_label(value, variable_class, semantic_map_data=None):
    """
    Map a categorical value code to its valueMapping term label.

    Falls back to the raw value when no term targets it.
    """
    schema = semantic_map_data.get('schema', {}) if semantic_map_data else {}
    variables = schema.get('variables', {})
    prefixes = _schema_prefixes(semantic_map_data)
    expanded_value = _expand_prefix(value, prefixes)
    expanded_class = _expand_prefix(variable_class, prefixes)
    for var_data in variables.values():
        var_class = var_data.get('class', '')
        if var_class != variable_class and _expand_prefix(var_class, prefixes) != expanded_class:
            continue
        for term_key, term_data in var_data.get('valueMapping', {}).get('terms', {}).items():
            target = term_data.get('targetClass', '')
            if target == value or _expand_prefix(target, prefixes) == expanded_value:
                return term_key.replace('_', ' ').title()
    return str(value)


def load_aggregate_stats(aggregate_data):
    """
    Load the categorical and numerical statistics of the latest central aggregate snapshot.

    Accepts both the 'categorical'/'numerical' keys and the vantage6-native
    'categorical_general_statistics'/'numerical_general_statistics' keys, so raw
    central task exports also work.

    Parameters:
    aggregate_data (dict): The 'aggregate' section of the dashboard data, keyed by
                           ISO timestamp.

    Returns:
    tuple: The (categorical, numerical) DataFrames of the latest aggregate snapshot,
           empty when no aggregate data is present.
    """
    categorical = _load_stats_frame(None, ['variable', 'value', 'count'])
    numerical = _load_stats_frame(None, ['variable', 'statistic', 'value'])
    if not aggregate_data:
        return categorical, numerical
    latest = aggregate_data[max(aggregate_data.keys())]
    if not isinstance(latest, dict):
        return categorical, numerical
    categorical_raw = latest.get('categorical', latest.get('categorical_general_statistics'))
    numerical_raw = latest.get('numerical', latest.get('numerical_general_statistics'))
    categorical = _load_stats_frame(categorical_raw, ['variable', 'value', 'count']).dropna(subset=['variable'])
    numerical = _load_stats_frame(numerical_raw, ['variable', 'statistic', 'value']).dropna(subset=['variable'])
    return categorical, numerical


# For a normal distribution the IQR spans q1..q3 = mu +/- z*sigma with z ~ 0.6745
_QUARTILE_Z = 0.6744897501960817
# Number of evenly spaced grid points the density curve is evaluated on
_CURVE_GRID_POINTS = 500


def generate_distribution_curve_figure(aggregate_data, variable, semantic_map_data=None):
    """
    Generate a density curve of one continuous variable, reconstructed from the
    central aggregate quartiles (q1, median, q3).

    The central v6-descriptive-statistics result carries the federated q1, median
    and q3 per variable (the algorithm removes min and max), so the distribution
    is modelled from the quartiles alone: a log-normal when the quartiles are
    right-skewed and strictly positive (the log transform makes it normal), a
    normal otherwise. In both cases sigma follows from the IQR = q3 - q1 via
    IQR = 2*z*sigma. The curve is evaluated on a dense, evenly spaced grid, the
    IQR band (q1..q3) is shaded and the median is marked.

    Parameters:
    aggregate_data (dict): The 'aggregate' section of the dashboard data.
    variable (str): The ontology class code of the variable to plot.
    semantic_map_data (dict, optional): The semantic map used for the variable label.

    Returns:
    plotly.graph_objs._figure.Figure: The density curve, or an annotation figure when
                                      no aggregate result or quartiles are available.
    """
    if not aggregate_data:
        return _empty_annotation_figure('No central aggregate result available')
    if not variable:
        return _empty_annotation_figure('Select a variable to visualise its distribution')
    label = _readable_variable_name(variable, semantic_map_data)
    _, numerical = load_aggregate_stats(aggregate_data)
    rows = numerical[numerical['variable'] == variable]
    stats = dict(zip(rows['statistic'], rows['value']))
    if not all(stat in stats for stat in ('q1', 'median', 'q3')):
        return _empty_annotation_figure(f'No quartile statistics available for {label}')

    q1, median, q3 = float(stats['q1']), float(stats['median']), float(stats['q3'])
    iqr = q3 - q1
    if iqr <= 0:
        return _empty_annotation_figure(f'Degenerate IQR of 0 for {label}')

    right_skewed = q1 > 0 and (q3 - median) > (median - q1)
    if right_skewed:
        # Log transform: the log-normal median is exp(mu) and its log-scale
        # quartiles are mu +/- z*sigma, so sigma = ln(q3/q1) / (2*z)
        mu = math.log(median)
        sigma = math.log(q3 / q1) / (2 * _QUARTILE_Z)
        x = np.linspace(math.exp(mu - 4 * sigma), math.exp(mu + 4 * sigma), _CURVE_GRID_POINTS)
        y = np.exp(-((np.log(x) - mu) ** 2) / (2 * sigma ** 2)) / (x * sigma * math.sqrt(2 * math.pi))
    else:
        mu = median
        sigma = iqr / (2 * _QUARTILE_Z)
        x_lo = max(0.0, mu - 4 * sigma) if q1 > 0 else mu - 4 * sigma
        x = np.linspace(x_lo, mu + 4 * sigma, _CURVE_GRID_POINTS)
        y = np.exp(-((x - mu) ** 2) / (2 * sigma ** 2)) / (sigma * math.sqrt(2 * math.pi))

    curve_color = pio.templates[pio.templates.default].layout.colorway[0]
    figure = go.Figure(go.Scatter(
        x=x,
        y=y,
        mode='lines',
        fill='tozeroy',
        name=label,
        line=dict(color=curve_color, width=2),
        hovertemplate=(
            f"<b>{label}</b><br>"
            "Value: <b>%{x:.2f}</b><br>"
            "Density: <b>%{y:.4f}</b><extra></extra>"
        ),
    ))

    # Shade the IQR band and mark the median
    figure.add_shape(
        type='rect', x0=q1, x1=q3, y0=0, y1=1, yref='paper',
        fillcolor=f'rgba(72, 72, 72, 0.15)', line=dict(width=0),
    )
    figure.add_shape(
        type='line', x0=median, x1=median, y0=0, y1=1, yref='paper',
        line=dict(color='#484848', width=2, dash='dash'),
    )

    figure.update_layout(
        title=f'Federated distribution of {label}',
        hoverlabel=dict(font_family='Poppins, sans-serif'),
        font=dict(family='Poppins, sans-serif'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(l=60, r=20, t=40, b=40),
        xaxis=dict(title=label),
        yaxis=dict(title='Density', rangemode='tozero'),
    )
    return _finalize_figure(figure)


def format_distribution_stats(aggregate_data, variable):
    """
    Format the quartile statistics of one variable from the central aggregate
    result as a one-line summary (Q1, median, Q3, IQR, mean, std, n, transform),
    rendered next to the distribution curve instead of inside the graph.

    Parameters:
    aggregate_data (dict): The 'aggregate' section of the dashboard data.
    variable (str): The ontology class code of the variable.

    Returns:
    str: The summary line, or an empty string when no quartiles are available.
    """
    if not aggregate_data or not variable:
        return ''
    _, numerical = load_aggregate_stats(aggregate_data)
    rows = numerical[numerical['variable'] == variable]
    stats = dict(zip(rows['statistic'], rows['value']))
    if not all(stat in stats for stat in ('q1', 'median', 'q3')):
        return ''

    q1, median, q3 = float(stats['q1']), float(stats['median']), float(stats['q3'])
    iqr = q3 - q1
    right_skewed = q1 > 0 and (q3 - median) > (median - q1)
    text = f'Q1: {q1:.2f} | Median: {median:.2f} | Q3: {q3:.2f} | IQR: {iqr:.2f}'
    if 'mean' in stats:
        text += f' | Mean: {float(stats["mean"]):.2f}'
    if 'std' in stats:
        text += f' | Std: {float(stats["std"]):.2f}'
    if 'count' in stats:
        text += f' | n: {float(stats["count"]):.0f}'
    text += ' (log-transformed)' if right_skewed else ' (normal)'
    return text


def _donut_figure(labels, values):
    """
    Build a donut (pie with a hole) figure from parallel label/value lists.

    The figure carries no title on purpose: the tile around the chart provides it.

    Parameters:
    labels (list): The sector labels.
    values (list): The sector values.

    Returns:
    plotly.graph_objs._figure.Figure: The donut figure.
    """
    figure = go.Figure(data=[
        dict(
            labels=labels,
            values=values,
            type='pie',
            hole=.56,
            name='',
            textinfo='value',
            hovertemplate=("<b>%{label}</b><br>"
                           "Count: <b>%{value}</b><br>"
                           "Proportion: <b>%{percent}</b><extra></extra>"),
        )
    ])
    figure.update_layout(
        hoverlabel=dict(font_family='Poppins, sans-serif'),
        font=dict(family='Poppins, sans-serif'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', yanchor='top', y=0, xanchor='center', x=0.5),
    )
    return _finalize_figure(figure)


# Special dropdown value for the ICD-10 binned cancer type groups
CANCER_GROUPS_VARIABLE = 'cancer_groups'


def categorical_value_counts(descriptive_data, selection, variable, semantic_map_data=None):
    """
    Aggregate the counts of one categorical variable over the selected organisations
    in the latest snapshot.

    variable is a schema variable name (e.g. 'biological_sex'), resolved to its
    ontology class via the semantic map, or the special value 'cancer_groups',
    which bins all ICD-10 coded variables into ICD-10 blocks. Value labels come
    from the schema valueMapping terms when available; the bookkeeping 'outliers'
    value is excluded and 'nan' is labelled 'Missing'.

    Parameters:
    descriptive_data (dict): The descriptive data; each key is a timestamp and each
                             value maps organisations to their statistics.
    selection (list): The selected organisation names.
    variable (str): The schema variable name, or 'cancer_groups'.
    semantic_map_data (dict, optional): The semantic map used for labels.

    Returns:
    tuple: (labels, values) sorted by count descending, or None when there is
           nothing to show.
    """
    if not descriptive_data or not selection or not variable:
        return None
    latest_data = descriptive_data[max(descriptive_data.keys())]
    frames = []
    for org in selection:
        if org in latest_data:
            categorical, _ = _load_organization_stats(latest_data[org])
            frames.append(categorical)
    if not frames:
        return None
    combined = pd.concat(frames, ignore_index=True)

    if variable == CANCER_GROUPS_VARIABLE:
        blocks = bin_icd10_blocks(combined)
        if blocks.empty:
            return None
        blocks = blocks.sort_values('count', ascending=False).reset_index(drop=True)
        labels = []
        for block in blocks['block']:
            try:
                description = icd10.get_description(block)
            except Exception:
                description = None
            labels.append(f'{block} - {description}' if description else str(block))
        return labels, [float(count) for count in blocks['count']]

    variable_class = _variable_class(variable, semantic_map_data)
    counts = defaultdict(float)
    rows = combined[combined['variable'] == variable_class]
    for value, count in zip(rows['value'], rows['count']):
        if str(value).lower() == 'outliers':
            continue
        counts[value] += count
    if not counts:
        return None
    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    labels = ['Missing' if str(value).lower() == 'nan'
              else _value_label(value, variable_class, semantic_map_data) for value, _ in items]
    return labels, [count for _, count in items]


def generate_categorical_pie_figure(descriptive_data, selection, variable, semantic_map_data=None, text="AYA"):
    """
    Generate a donut chart of the counts of one categorical variable (see
    categorical_value_counts). The figure has no title; the tile around the
    chart provides it.

    Returns:
    plotly.graph_objs._figure.Figure: The donut chart, or an annotation figure.
    """
    if not descriptive_data:
        return _empty_annotation_figure(f'No {text} data available')
    if not selection:
        return _empty_annotation_figure('Select an organisation to visualise the variable distribution')
    if not variable:
        return _empty_annotation_figure('Select a variable to visualise')
    counts = categorical_value_counts(descriptive_data, selection, variable, semantic_map_data)
    if counts is None:
        return _empty_annotation_figure('No data available for the selected organisations and variable')
    return _donut_figure(*counts)


def generate_categorical_bar_figure(descriptive_data, selection, variable, semantic_map_data=None, text="AYA"):
    """
    Generate a horizontal bar chart of the counts of one categorical variable
    (see categorical_value_counts), largest bar on top. The figure has no title;
    the tile around the chart provides it.

    Returns:
    plotly.graph_objs._figure.Figure: The bar chart, or an annotation figure.
    """
    if not descriptive_data:
        return _empty_annotation_figure(f'No {text} data available')
    if not selection:
        return _empty_annotation_figure('Select an organisation to visualise the variable distribution')
    if not variable:
        return _empty_annotation_figure('Select a variable to visualise')
    counts = categorical_value_counts(descriptive_data, selection, variable, semantic_map_data)
    if counts is None:
        return _empty_annotation_figure('No data available for the selected organisations and variable')

    labels, values = counts
    # ascending order so the largest bar ends up on top
    order = sorted(range(len(values)), key=lambda i: values[i])
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]

    figure = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation='h',
        hovertemplate=("<b>%{y}</b><br>"
                       "Count: <b>%{x}</b><extra></extra>"),
    ))
    figure.update_layout(
        hoverlabel=dict(font_family='Poppins, sans-serif'),
        font=dict(family='Poppins, sans-serif'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=max(400, len(labels) * 28 + 200),
        margin=dict(l=260, r=20, t=20, b=40),
        xaxis=dict(title=f'Number of {text}s', rangemode='tozero'),
        yaxis=dict(title=None, automargin=True),
    )
    return _finalize_figure(figure)


def format_categorical_csv(labels, values):
    """
    Format categorical counts as CSV text with a 'category,count' header.

    Parameters:
    labels (list): The category labels.
    values (list): The counts.

    Returns:
    str: The CSV text.
    """
    lines = ['category,count']
    for label, value in zip(labels, values):
        safe_label = str(label).replace('"', '""')
        lines.append(f'"{safe_label}",{value:g}')
    return '\n'.join(lines) + '\n'


# Values that are bookkeeping rows rather than actual categories
SPECIAL_CATEGORICAL_VALUES = ['na', 'outliers', '']


def _get_icd10_block(code):
    """
    Determine the ICD-10 block (e.g. 'C50-C50') that the given ICD-10 code belongs to.

    Parameters:
    code: The ICD-10 code (e.g. 'C50.9').

    Returns:
    str: The block code, or None if the code is not a valid ICD-10 item.
    """
    try:
        code = str(code).strip()
        if not code or not icd10.is_valid_item(code):
            return None
        if icd10.is_block(code):
            return code
        # Walk up the ancestors (from closest to furthest) until we find the block
        for ancestor in icd10.get_ancestors(code):
            if icd10.is_block(ancestor):
                return ancestor
        return None
    except Exception:
        return None


def detect_icd10_variables(categorical_df, minimum_valid_fraction=0.5):
    """
    Detect which categorical variables actually contain ICD-10 codes.

    The variable holding the ICD-10 codes cannot reliably be recognised by its
    name, so it is detected by the shape of its values: at least
    minimum_valid_fraction of a variable's non-bookkeeping values must be valid
    ICD-10 items.

    Parameters:
    categorical_df (pd.DataFrame): Categorical statistics with 'variable', 'value'
                                   and 'count' columns.
    minimum_valid_fraction (float): Minimum fraction of valid ICD-10 items required.

    Returns:
    list: The variable codes that contain ICD-10 codes.
    """
    icd10_variables = []
    if categorical_df.empty:
        return icd10_variables
    for variable, var_rows in categorical_df.groupby('variable', sort=False):
        values = var_rows['value'].dropna()
        values = values[~values.astype(str).str.strip().str.lower().isin(SPECIAL_CATEGORICAL_VALUES)]
        if values.empty:
            continue
        valid_count = sum(_get_icd10_block(value) is not None for value in values)
        if valid_count and valid_count / len(values) >= minimum_valid_fraction:
            icd10_variables.append(variable)
    return icd10_variables


def bin_icd10_blocks(categorical_df):
    """
    Aggregate ICD-10 coded categorical values into block-level counts.

    Mirrors add_binned_icd10_categories from the vantage6-sandbox
    run-descriptive-statistics notebook: ICD-10 variables are detected by value
    shape and each code is mapped to its ICD-10 block.

    Parameters:
    categorical_df (pd.DataFrame): Categorical statistics with 'variable', 'value'
                                   and 'count' columns.

    Returns:
    pd.DataFrame: Columns 'block' and 'count', summed per block; empty when no
                  ICD-10 coded values are present.
    """
    blocks = pd.DataFrame(columns=['block', 'count'])
    for variable in detect_icd10_variables(categorical_df):
        var_rows = categorical_df[categorical_df['variable'] == variable].copy()
        var_rows = var_rows[
            ~var_rows['value'].astype(str).str.strip().str.lower().isin(SPECIAL_CATEGORICAL_VALUES)
            & var_rows['value'].notna()
        ]
        if var_rows.empty:
            continue
        var_rows['block'] = var_rows['value'].apply(_get_icd10_block)
        var_rows = var_rows[var_rows['block'].notna()]
        if var_rows.empty:
            continue
        var_rows['count'] = pd.to_numeric(var_rows['count'], errors='coerce')
        grouped = var_rows.groupby('block')['count'].sum().reset_index()
        grouped.columns = ['block', 'count']
        blocks = pd.concat([blocks, grouped], ignore_index=True)
    if blocks.empty:
        return blocks
    return blocks.groupby('block')['count'].sum().reset_index()


def detect_icd10_variables_in_data(descriptive_data):
    """
    Detect ICD-10 coded categorical variables across all organisations of the
    latest snapshot. Used to decide whether the 'cancer_groups' dropdown option
    should be offered.

    Parameters:
    descriptive_data (dict): The descriptive data; each key is a timestamp and each
                             value maps organisations to their statistics.

    Returns:
    list: The variable codes that contain ICD-10 codes.
    """
    if not descriptive_data:
        return []
    latest_data = descriptive_data[max(descriptive_data.keys())]
    frames = []
    for org_data in latest_data.values():
        categorical, _ = _load_organization_stats(org_data)
        frames.append(categorical)
    if not frames:
        return []
    return detect_icd10_variables(pd.concat(frames, ignore_index=True))
