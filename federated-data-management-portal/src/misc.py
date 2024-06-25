import json
import os

from datetime import datetime

# internal dependencies
from .vantage_client import retrieve_triplestore_collaboration_descriptives


def fetch_data(vantage6_config, descriptive_data):
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

    Returns:
    dict: The updated descriptive data with the fetched data appended.
    """
    if vantage6_config is None:
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
        if all(value is None for value in config.values()):
            config = None
    else:
        config = vantage6_config

    if config is not None:
        # Fetch the new data from your task
        _new_data = json.loads(retrieve_triplestore_collaboration_descriptives(config))

        # Clear the config; keep Docker's secrets, secret
        del config

    else:
        _new_data = json.load(open(f'example_data{os.path.sep}mockresult.json', 'r'))

    try:
        new_data = {item['organisation']: {k: v for k, v in item.items() if k != 'organisation'} for item in
                    _new_data}
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