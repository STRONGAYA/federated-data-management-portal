import json
import os

import pandas as pd

from datetime import datetime
from .vantage_client import retrieve_descriptive_statistics


def fetch_data(vantage6_config, descriptive_data, semantic_map):
    """
    This function fetches data from a vantage6 task or from a local JSON file.

    If a vantage6 configuration is provided, it uses this configuration to retrieve data from a vantage6 task.
    If no configuration is provided,
    it reads data from a local JSON file named 'mockresult.json' in the 'example_data' directory.

    The function also adds a timestamp to the fetched data and appends it to the existing descriptive data.

    Parameters:
    vantage6_config (dict): The vantage6 configuration to use for retrieving data from a vantage6 task.
                            If None, data is read from a local JSON file.
    descriptive_data (dict): The existing descriptive data to append the fetched data to.
                             If None, a new dictionary is created.
    semantic_map (dict): The semantic_map defining the structure of the data; see the 'semantic_map' variable in the 'main.py' file.

    Returns:
    dict: The updated descriptive data with the fetched data appended.
    """
    if vantage6_config is None:
        # TODO correct this with new config setup; aggregating organisation doesnt exist anymore
        config = {
            'collaboration': read_docker_secret('vantage6_collaboration'),
            'aggregating_organisation': read_docker_secret('vantage6_aggregating_organisation'),
            'server_url': read_docker_secret('vantage6_server_url'),
            'server_port': read_docker_secret('vantage6_server_port'),
            'server_api': read_docker_secret('vantage6_server_api'),
            'username': read_docker_secret('vantage6_service_username'),
            'password': read_docker_secret('vantage6_service_password'),
            'organization_key': read_docker_secret('vantage6_private_key_path')
        }
        
        # Try to read organization information from Docker secrets
        organizations_secret = read_docker_secret('vantage6_organizations')
        if organizations_secret:
            try:
                config['organizations'] = json.loads(organizations_secret)
            except json.JSONDecodeError:
                print("Warning: Could not parse organizations from Docker secret, using fallback")
                config['organizations'] = [
                    {
                        "organisation": "Default Organization",
                        "country": "Unknown",
                        "organisation_identifier": 1
                    }
                ]
        else:
            # Fallback organization structure if no secret is provided
            config['organizations'] = [
                {
                    "organisation": "Default Organization", 
                    "country": "Unknown",
                    "organisation_identifier": 1
                }
            ]
        
        if all(value is None for key, value in config.items() if key != 'organizations'):
            config = None
    else:
        config = vantage6_config

    variables_to_describe = {}
    for value in semantic_map.values():
        if any(reconstruction.get('type') == 'node' for reconstruction in value.get('schema_reconstruction', [])):
            variables_to_describe[value['class']] = {'datatype': 'numerical'}
        else:
            variables_to_describe[value['class']] = {'datatype': 'categorical'}

    if config is not None:
        # Use hardcoded organization information from config
        if 'organizations' in config:
            _new_data = config['organizations']
        else:
            # Fallback to default organization data if not provided in config
            _new_data = [
                {
                    "organisation": "Not available",
                    "country": "Not available",
                    "organisation_identifier": 1
                }
            ]

        # Collect results from each organization
        all_partial_results = []
        
        for org_info in _new_data:
            org_id = org_info.get('organisation_identifier')
            if org_id:
                # Fetch the descriptive statistics from each organization
                org_stats_raw = json.loads(retrieve_descriptive_statistics(config, org_id, variables_to_describe))

                # Convert the new format to the expected format
                org_stats = {
                    'organisation': org_info['organisation'],
                    'categorical': org_stats_raw.get('categorical_general_partial_statistics', '{}').replace("http:\/\/ncicb.nci.nih.gov\/xml\/owl\/EVS\/Thesaurus.owl#", "ncit:"),
                    'numerical': org_stats_raw.get('numerical_general_partial_statistics', '{}').replace("http:\/\/ncicb.nci.nih.gov\/xml\/owl\/EVS\/Thesaurus.owl#", "ncit:"),
                }
                all_partial_results.append(org_stats)

        # Combine all partial results into the expected format
        _new_descriptive_stats = {'partial_results': all_partial_results}

        # Clear the config; keep Docker's secrets, secret
        del config

    else:
        directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _new_data = json.load(
            open(rf"{directory}{os.path.sep}example_data{os.path.sep}mock_descriptives_collaboration.json", 'r'))
        _new_descriptive_stats = json.load(
            open(rf"{directory}{os.path.sep}example_data{os.path.sep}mock_descriptive_statistics.json", 'r'))
    try:
        new_data = {item['organisation']: {k: v for k, v in item.items() if k != 'organisation'} for item in _new_data}

        # Create a mapping of class codes to names TODO, do we still need this?
        variable_class_code_to_name = {v['class']: k for k, v in semantic_map.items()}
        value_class_code_to_name = {}
        for variable in variable_class_code_to_name.values():
            if semantic_map[variable].get('value_mapping') is not None:
                for value in semantic_map[variable].get('value_mapping').get('terms'):
                    value_class_code_to_name.update({semantic_map[variable].get(
                        'value_mapping').get('terms').get(value).get('target_class'): value})

        # Combine the new data with the descriptive statistics
        _partial_stats = _new_descriptive_stats['partial_results']
        _new_stats = {item['organisation']: item for item in _partial_stats}

        for org in new_data:
            if org in _new_stats:

                # Support both new and old format for backwards compatibility
                org_stats = _new_stats[org]
                update_dict = {}

                # Handle categorical data - check for new format first, then old format
                if 'categorical_general_partial_statistics' in org_stats:
                    categorical_data = pd.DataFrame(json.loads(org_stats['categorical_general_partial_statistics']))
                    update_dict['categorical'] = categorical_data.to_json()
                elif 'categorical' in org_stats:
                    categorical_data = pd.DataFrame(json.loads(org_stats['categorical']))
                    update_dict['categorical'] = categorical_data.to_json()
                
                # Handle numerical data - check for new format first, then old format  
                if 'numerical_general_partial_statistics' in org_stats:
                    numerical_data = pd.DataFrame(json.loads(org_stats['numerical_general_partial_statistics']))
                    update_dict['numerical'] = numerical_data.to_json()
                elif 'numerical' in org_stats:
                    numerical_data = pd.DataFrame(json.loads(org_stats['numerical']))
                    update_dict['numerical'] = numerical_data.to_json()
                
                new_data[org].update(update_dict)

    except TypeError:
        new_data = {}

    # Get the current timestamp
    current_timestamp = datetime.now().isoformat()

    # If data is not None, add the new data to it
    if descriptive_data is not None:
        descriptive_data[current_timestamp] = new_data
    else:
        descriptive_data = {current_timestamp: new_data}

    return descriptive_data


def read_docker_secret(secret_name):
    """
    This function reads a Docker secret.

    Docker secrets are a secure way to store sensitive information such as passwords, API keys, and other credentials.
    These secrets are stored in the '/run/secrets/' directory inside the Docker container.

    Parameters:
    secret_name (str): The name of the Docker secret to read.

    Returns:
    str: The secret value as a string if the secret file exists, otherwise None.

    Raises:
    IOError: If there is an error opening the secret file.
    """
    try:
        with open(f'/run/secrets/{secret_name}', 'r') as secret_file:
            return secret_file.read().strip()
    except IOError:
        return None
