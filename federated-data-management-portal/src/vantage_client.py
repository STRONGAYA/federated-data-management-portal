from vantage6.client import UserClient as Client


def retrieve_triplestore_collaboration_descriptives(config):
    """
    This function retrieves descriptive data the triplestore database(s).

    It authenticates a client, creates a task for the client to retrieve the
    descriptive data, waits for the results to be ready, and then returns the results.

    Parameters:
    config (object): An object containing configuration details.
    It should have the following attributes:
        - collaboration: The collaboration ID.
        - aggregating_organisation: The organisation ID of the aggregating organisation.
        - server_url: The server URL.
        - server_port: The server port.
        - server_api: The server API.
        - username: The username for authentication.
        - password: The password for authentication.
        - organization_key: The private key of the user's organisation to set up end-to-end encryption.

    Returns:
        dict: A dictionary containing the result data.
    """
    try:
        # Authenticate the client
        client = _authenticate(config)
    except Exception as e:
        print(f"ERROR - Vantage6 implementation - Attempting to authenticate the Vantage6 user resulted in an error, "
              f"is the configuration correct?\n"
              f"error: {e}")
        return """[
            {
                "organisation": "Not available:",
                "country": "Not available",
                "sample_size": 0,
                "variable_info": []
            }
        ]"""

    # When passed as Docker secrets, the values might be passed as strings
    if isinstance(config.get('collaboration'), str):
        config['collaboration'] = int(config.get('collaboration'))
    if isinstance(config.get('aggregating_organisation'), str):
        config['aggregating_organisation'] = [int(config.get('aggregating_organisation'))]

    if isinstance(config.get('aggregating_organisation'), int):
        config['aggregating_organisation'] = [config.get('aggregating_organisation')]

    # Create a task for the client to retrieve the descriptive data
    task = client.task.create(
        collaboration=config.get('collaboration'),
        organizations=config.get('aggregating_organisation'),
        name="Data management descriptive info retrieval",
        image="ghcr.io/strongaya/v6-triplestore-collaboration-descriptives:v1.0.0",
        description='Task to retrieve the triplestore descriptives in light of a data management portal.',
        input_={'method': 'central'},
        databases=[{'label': 'default'}]
    )

    # Wait for results to be ready
    print("Waiting for results")
    task_id = task['id']
    _result = client.wait_for_results(task_id)

    # Retrieve the results
    result = client.result.from_task(task_id=task_id)
    return result['data'][0]['result']


def retrieve_descriptive_statistics(config, variables_to_describe):
    """
    This function retrieves descriptive statistics the triplestore database(s).

    It authenticates a client, creates a task for the client to retrieve the
    descriptive data, waits for the results to be ready, and then returns the results.

    Parameters:
    config (object): An object containing configuration details.
    It should have the following attributes:
        - collaboration: The collaboration ID.
        - aggregating_organisation: The organisation ID of the aggregating organisation.
        - server_url: The server URL.
        - server_port: The server port.
        - server_api: The server API.
        - username: The username for authentication.
        - password: The password for authentication.
        - organization_key: The private key of the user's organisation to set up end-to-end encryption.
    variables_to_describe (dict): A dictionary containing the variables to describe.
    It should at least have the following structure:
        {
            'variable_name_1': {
                'datatype': 'categorical' or 'numerical'
            },
            'variable_name_2': {
                'datatype': 'categorical' or 'numerical'
            },
            ...
        }

    Returns:
        dict: A dictionary containing the result data.
    """
    try:
        # Authenticate the client
        client = _authenticate(config)
    except Exception as e:
        print(f"ERROR - Vantage6 implementation - Attempting to authenticate the Vantage6 user resulted in an error, "
              f"is the configuration correct?\n"
              f"error: {e}")
        return """[
        {
          "partial_results": [
            {
              "organisation_name": "",
              "categorical": "{},\"count\":{}}",
              "numerical": "{\"variable\":{},\"statistic\":{}}",
              "excluded_variables": []
            },
            {
              "organisation_name": "",
              "categorical": "{\"variable\":{},\"value\":{}}",
              "numerical": "{\"variable\":{},\"statistic\":{}}",
              "excluded_variables": []
            },
            {
              "organisation_name": "",
              "categorical": "{\"variable\":{}, \"value\":{}}",
              "numerical": "{\"variable\":{},\"statistic\":{}}",
              "excluded_variables": []
            }
          ]
        }
        ]"""

    # When passed as Docker secrets, the values might be passed as strings
    if isinstance(config.get('collaboration'), str):
        config['collaboration'] = int(config.get('collaboration'))
    if isinstance(config.get('aggregating_organisation'), str):
        config['aggregating_organisation'] = [int(config.get('aggregating_organisation'))]

    if isinstance(config.get('aggregating_organisation'), int):
        config['aggregating_organisation'] = [config.get('aggregating_organisation')]

    # Create a task for the client to retrieve the descriptive data
    task = client.task.create(
        collaboration=config.get('collaboration'),
        organizations=config.get('aggregating_organisation'),
        name="Data management descriptive statistics",
        image="ghcr.io/strongaya/v6-descriptive-statistics:v1.0.0",
        description='Task to retrieve the descriptive statistics in light of a data management portal.',
        input_={'method': 'central',
                'kwargs': {
                    'variables_to_describe': variables_to_describe,
                    'return_partials': True
                }},
        databases=[{'label': 'default'}]
    )

    # Wait for results to be ready
    print("Waiting for results")
    task_id = task['id']
    _result = client.wait_for_results(task_id)

    # Retrieve the results
    result = client.result.from_task(task_id=task_id)
    return result['data'][0]['result']


def _authenticate(config):
    """
    This function authenticates a client.

    It creates a client with the given configuration details, authenticates the client,
    and sets up encryption for the client.

    Parameters:
    config (object): An object containing configuration details.
    It should have the following attributes:
        - server_url: The server URL.
        - server_port: The server port.
        - server_api: The server API.
        - username: The username for authentication.
        - password: The password for authentication.
        - organization_key: The private key of the user's organisation to set up end-to-end encryption.

    Returns:
        Client: An authenticated client with encryption set up.
    """
    # Create a client
    client = Client(config.get('server_url'), config.get('server_port'), config.get('server_api'),
                    log_level='debug')
    # Authenticate the client
    client.authenticate(config.get('username'), config.get('password'))

    # Set up encryption for the client
    if config.get('organization_key') == '':
        config['organization_key'] = None
    client.setup_encryption(config.get('organization_key'))

    return client
