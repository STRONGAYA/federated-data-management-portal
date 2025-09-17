import copy
import io
import json
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from collections import defaultdict
from dash import dash_table
from dash import html
from datetime import datetime

names_to_capitalise = ["eortc", "hads"]


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
    
    # First, try to find ncit:C164339 variable (preferred sample size variable)
    target_variable = "ncit:C164339"
    found_target = False
    
    # Check categorical data for ncit:C164339
    if 'categorical' in org_data:
        try:
            categorical_df = pd.DataFrame(json.loads(org_data['categorical']))
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
    if not found_target and 'numerical' in org_data:
        try:
            numerical_df = pd.DataFrame(json.loads(org_data['numerical']))
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
        if 'numerical' in org_data:
            try:
                numerical_df = pd.DataFrame(json.loads(org_data['numerical']))
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
        if max_count == 0 and 'categorical' in org_data:
            try:
                categorical_df = pd.DataFrame(json.loads(org_data['categorical']))
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
            if 'categorical' in org_data:
                categorical_df = pd.DataFrame(json.loads(org_data['categorical']))
                mask = categorical_df['variable'].apply(
                    lambda x: any(x.startswith(prefix) for prefix in selected_prefixes)
                )
                filtered_categorical = categorical_df[mask]
                filtered_data[timestamp][org]['categorical'] = filtered_categorical.to_json()

            # Filter numerical data
            if 'numerical' in org_data:
                numerical_df = pd.DataFrame(json.loads(org_data['numerical']))
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
    semantic_map_data (dict): Semantic_map data containing variable_info with schema_reconstruction
    max_depth (int): Maximum depth to check in schema_reconstruction

    Returns:
    dict: Filtered descriptive data containing only variables with matching categories
    """
    if not descriptive_data or not selected_categories or not semantic_map_data:
        return descriptive_data

    # Create mapping from category values to aesthetic labels
    category_mapping = {}
    for cat in selected_categories:
        # Convert back from value format to aesthetic label with proper spacing
        category_mapping[cat] = cat.replace('_', ' ').title()

    # Get variables that belong to selected categories
    selected_variables = set()
    if 'variable_info' in semantic_map_data:
        for variable_name, variable_data in semantic_map_data['variable_info'].items():
            if 'schema_reconstruction' in variable_data and variable_data['schema_reconstruction']:
                # Check each level in schema_reconstruction up to max_depth
                # Only look at class items (not nodes) within the specified depth
                for level, reconstruction_item in enumerate(variable_data['schema_reconstruction']):
                    if level >= max_depth:
                        break
                    
                    if (reconstruction_item.get('type') == 'class' and 
                        'aesthetic_label' in reconstruction_item and
                        reconstruction_item.get('placement') != 'before'):
                        # Remove underscores from aesthetic label and normalize
                        aesthetic_label = reconstruction_item['aesthetic_label'].replace('_', ' ')
                        # Check if this variable belongs to any selected category
                        for cat_value, cat_label in category_mapping.items():
                            if aesthetic_label.lower() == cat_label.lower():
                                selected_variables.add(variable_name)
                                break

    if not selected_variables:
        return descriptive_data

    filtered_data = {}

    for timestamp, data in descriptive_data.items():
        filtered_data[timestamp] = {}

        for org, org_data in data.items():
            filtered_data[timestamp][org] = org_data.copy()

            # Filter categorical data
            if 'categorical' in org_data:
                categorical_df = pd.DataFrame(json.loads(org_data['categorical']))
                mask = categorical_df['variable'].isin(selected_variables)
                filtered_categorical = categorical_df[mask]
                filtered_data[timestamp][org]['categorical'] = filtered_categorical.to_json()

            # Filter numerical data
            if 'numerical' in org_data:
                numerical_df = pd.DataFrame(json.loads(org_data['numerical']))
                mask = numerical_df['variable'].isin(selected_variables)
                filtered_numerical = numerical_df[mask]
                filtered_data[timestamp][org]['numerical'] = filtered_numerical.to_json()

    return filtered_data


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

        # Create the data for the bar chart
        data = [
            dict(
                x=[proportions[i]],
                y=[f'Number of {text}s per organisation'],
                name=org,
                type='bar',
                orientation='h',
                marker=dict(line=dict(width=0)),
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
                'barmode': 'stack',
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
        return figure


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
    prefixes = dict(re.findall(r'PREFIX (\w+): <([^>]+)>', global_semantic_map_data.get('prefixes', '')))
    prefixes['ncit'] = r'http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#'

    variable_info = global_semantic_map_data.get('variable_info')
    if variable_info is None:
        variable_info = {}

    # Find the most recent timestamp
    most_recent_timestamp = max(descriptive_data.keys(), key=lambda x: datetime.fromisoformat(x))

    # Select the data associated with the most recent timestamp
    descriptive_data_most_recent = descriptive_data[most_recent_timestamp]

    # Get the list of organizations from the descriptive data
    organizations = list(descriptive_data_most_recent.keys())

    _variable_info = copy.deepcopy(variable_info)


    # For each variable in the semantic map, create a row using categorical and numerical statistics
    for variable in variable_info.keys():
        org_variable_counts = {}
        variable_class = _variable_info[variable].get("class")

        for organisation in organizations:
            org_data = descriptive_data_most_recent[organisation]
            total_available = 0
            
            # Process categorical data for this variable
            if 'categorical' in org_data:
                try:
                    categorical_df = pd.DataFrame(json.loads(org_data['categorical']))
                    # Find rows for this variable (excluding nan values)
                    # The variable names should be already mapped from class codes in misc.py
                    var_data = categorical_df[
                        (categorical_df['variable'] == variable_class) &
                        (categorical_df['value'] != 'nan')
                    ]
                    total_available += var_data['count'].sum()
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Process numerical data for this variable  
            if 'numerical' in org_data:
                try:
                    numerical_df = pd.DataFrame(json.loads(org_data['numerical']))
                    # Find rows for this variable with 'count' statistic
                    var_data = numerical_df[
                        (numerical_df['variable'] == variable_class) &
                        (numerical_df['statistic'] == 'count')
                    ]
                    total_available += var_data['value'].sum()
                except (json.JSONDecodeError, KeyError):
                    pass
            
            org_variable_counts[organisation] = int(total_available)

        # Compute the total count across all organizations
        total_count = sum(org_variable_counts.values())

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
            value_mapping = _variable_info[variable].get('value_mapping', {})
            
            # Determine if this variable should be subject to value class checking
            should_check_value_classes = False
            if value_mapping and value_mapping.get('terms') and count > 0:
                # Check if there are any terms other than 'missing_or_unspecified'
                non_missing_terms = [term for term in value_mapping.get('terms', {}).keys() 
                                   if term != 'missing_or_unspecified']
                should_check_value_classes = len(non_missing_terms) > 0
            
            if should_check_value_classes:
                org_data = descriptive_data_most_recent[organisation]
                if 'categorical' in org_data:
                    try:
                        categorical_df = pd.DataFrame(json.loads(org_data['categorical']))
                        actual_values = categorical_df[
                            categorical_df['variable'] == variable_class
                        ]['value'].unique()
                        
                        # Check each expected value class
                        for term_key, value_info in value_mapping.get('terms', {}).items():
                            if term_key == 'missing_or_unspecified':
                                continue
                                
                            target_class = value_info.get('target_class', '')
                            
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
                if 'categorical' in org_data:
                    try:
                        categorical_df = pd.DataFrame(json.loads(org_data['categorical']))
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
                                
                            target_class = value_info.get('target_class', '')
                            
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
    _style_cell = {'fontSize': '14px', 'border': 'none', 'padding': '0px 0px 0px 0px', 'textOverflow': 'ellipsis',
                   'overflow': 'hidden'}
    _style_data = {'border': 'none'}
    _style_header = {'position': 'sticky', 'top': 0, 'backgroundColor': '#ffffff', 'fontWeight': 'bold'}

    data_table = dash_table.DataTable(
        id='table-data-availability',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        style_table=_style_table,
        style_cell={**_style_cell, 'width': '{}%'.format(100 / len(df.columns))},
        style_data=_style_data,
        style_header=_style_header,
        style_data_conditional=[
            {'if': {'column_id': col, 'filter_query': '{' + col + '} eq "' + symbol + '"'}, 'color': color}
            for col in df.columns[2:] for symbol, color in [('✔', 'green'), ('✖', 'red'), ('!', 'orange')]
        ],
        style_cell_conditional=[
            {'if': {'column_id': 'Variables'}, 'width': '20px'},
            *[
                {'if': {'column_id': col}, 'width': '10px'}
                for col in df.columns[1:]
            ]
        ],
        tooltip_data=[
            {column: {'value': str(tooltip[column]), 'type': 'markdown'}
            if column in tooltip else None for column in df.columns}
            for tooltip in tooltips
        ],
        fixed_columns={'headers': True, 'data': 2},
        tooltip_duration=None,
        filter_action="native",  # Enable search functionality
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
                    categorical_data = pd.DataFrame(json.loads(data["categorical"]))
                    numerical_data = pd.DataFrame(json.loads(data["numerical"]))

                    # Calculate total counts excluding 'nan' and 'outliers'
                    total_categorical_count = categorical_data[categorical_data["value"] != "nan"]["count"].sum()
                    total_numerical_count = numerical_data[numerical_data["statistic"] == "count"]["value"].sum()

                    # Calculate missing counts
                    missing_categorical_count = categorical_data[categorical_data["value"] == "nan"]["count"].sum()
                    missing_numerical_count = numerical_data[numerical_data["statistic"] == "nan"]["value"].sum()

                    # Sum relative missing counts
                    relative_missing_count = (missing_categorical_count + missing_numerical_count) / (
                            (total_categorical_count + missing_categorical_count) + (
                            total_numerical_count + missing_numerical_count))
                    missing_counts.append(total_categorical_count + total_numerical_count)
                    _custom_data.append((round((relative_missing_count * 100), 1)))

                title = f'Complete {text} data points per organisation'
                sample_sizes = missing_counts
            elif chart_type == "country":
                country_data = defaultdict(float)
                relative_country_data = defaultdict(float)
                for data in latest_data.values():
                    categorical_data = pd.DataFrame(json.loads(data["categorical"]))
                    numerical_data = pd.DataFrame(json.loads(data["numerical"]))

                    # Calculate total counts excluding 'nan' and 'outliers'
                    total_categorical_count = categorical_data[categorical_data["value"] != "nan"]["count"].sum()
                    total_numerical_count = numerical_data[numerical_data["statistic"] == "count"]["value"].sum()

                    # Calculate missing counts
                    missing_categorical_count = categorical_data[categorical_data["value"] == "nan"]["count"].sum()
                    missing_numerical_count = numerical_data[numerical_data["statistic"] == "nan"]["value"].sum()

                    # Sum relative missing counts
                    relative_missing_count = (missing_categorical_count + missing_numerical_count) / (
                            (total_categorical_count + missing_categorical_count) + (
                            total_numerical_count + missing_numerical_count))
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
                    categorical_data = pd.DataFrame(json.loads(data["categorical"]))
                    numerical_data = pd.DataFrame(json.loads(data["numerical"]))

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
                    categorical_data = pd.DataFrame(json.loads(data["categorical"]))
                    numerical_data = pd.DataFrame(json.loads(data["numerical"]))

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

        data = [
            dict(
                labels=labels,
                values=sample_sizes,
                type='pie',
                hole=.56,
                name='',
                hovertemplate=(hover),
                customdata=_custom_data,
                textinfo='value'
            )
        ]

        figure = go.Figure(data=data)

        figure.update_layout(
            title=title,
            hoverlabel=dict(font_family='Poppins, sans-serif'),
            font=dict(family='Poppins, sans-serif'),
            legend=dict(
                orientation='h',
                yanchor='top',
                y=0,
                xanchor='center',
                x=0.5,
            ),
        )

        return figure


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
            if semantic_map_data and 'variable_info' in semantic_map_data:
                variable_info = semantic_map_data['variable_info']
                # Expand prefixes in ontology code if needed
                expanded_code = ontology_code
                if 'prefixes' in semantic_map_data:
                    prefixes = dict(re.findall(r'PREFIX (\w+): <([^>]+)>', semantic_map_data.get('prefixes', '')))
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
                    if 'prefixes' in semantic_map_data:
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
                categorical_data = pd.DataFrame(json.loads(data["categorical"]))
                numerical_data = pd.DataFrame(json.loads(data["numerical"]))

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

            # Calculate percentages
            visualisation_df[f'Percentage available {text}s'] = visualisation_df[f'Total available {text}s'] / (
                    visualisation_df[f'Total available {text}s'] + visualisation_df[f'Total unavailable {text}s'])
            visualisation_df[f'Percentage unavailable {text}s'] = visualisation_df[f'Total unavailable {text}s'] / (
                    visualisation_df[f'Total available {text}s'] + visualisation_df[f'Total unavailable {text}s'])

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
                categorical_data = pd.DataFrame(json.loads(data["categorical"]))
                numerical_data = pd.DataFrame(json.loads(data["numerical"]))

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

            # Calculate percentages
            visualisation_df[f'Percentage available {text}s'] = visualisation_df[f'Total available {text}s'] / (
                    visualisation_df[f'Total available {text}s'] + visualisation_df[f'Total unavailable {text}s'])
            visualisation_df[f'Percentage unavailable {text}s'] = visualisation_df[f'Total unavailable {text}s'] / (
                    visualisation_df[f'Total available {text}s'] + visualisation_df[f'Total unavailable {text}s'])

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
            width=1100,
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

        return fig


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
        width=850,
        height=400,
        xanchor='center', yanchor='middle'
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig
