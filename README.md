# Federated Data Management Portal
This repository contains the code for the Federated Data Management Portal,
a web application that allows users to inspect data from multiple sources in a single interface.
The application has a Vantage6 integration that is automatically enabled when the application is started.
This integration will hereafter periodically repeat the task after a set interval 
(given the application is kept running).

The portal is built using Dash and Vantage6.  
The provided implementation has a large dependency on the collaboration descriptives algorithm,
please refer to its respective repository for more information
(https://github.com/STRONGAYA/triplestore-collaboration-descriptives).

## Prequisites
- ### When using the triplestore-collaboration-descriptives algorithm (default)
  - Vantage6 server and collaboration with nodes running on version 4.x.x
  - Distributed data in RDF-triple format 
  (produced using the Triplifier tool e.g. through https://github.com/MaastrichtU-CDS/Flyover)
  - Annotated data using the SIO's has-attribute relation 
  (http://semanticscience.org/resource/SIO_000008)
  - GraphDB instances running and accessible on distributed data stations
  - JSON file containing the expected schema (see `example_data/schema.json` for an example)
  - Credentials to send a task to the Vantage6 server
- ### In development mode
  - Python 3.10 environment with libraries in `requirements.txt` installed
  - Access to example data in `example_data/` or alternative data in the same format


## Running the application
### In Docker
The application can be run in a Docker container using the provided `docker-compose.yml` and `Dockerfile`.
However, the application uses Docker secrets to store Vantage6 server credentials, 
and for that reason we strongly recommend to use the provided shell script `start.sh` to run the application 
as the necessary secrets will then be prompted.  
This will appear as follows:
```bash
bash start.sh

# These example credentials can be found in `example_data/demo_network_config.json`

# "Please enter the username of the service account:"
# org_1-admin

# "Please enter the password of the service account:"
# password

# "Please enter the server URL:"
# http://host.docker.internal

# "Please enter the server port:"
# 5000

# "Please enter the server API path:"
# /api

# "Please enter the collaboration id:"
# 1

# "Please enter the path to the private key in case encryption is enabled for this collaboration:"
# (leave blank if unencrypted)

# "Please enter the id of the aggregating organisation:"
# 1

# "Please enter the path to the schema JSON file:"
# example_data/schema.json
```
The application should now be running and available on `http://localhost:8050`.

You can stop and remove the set Docker secrets using the provided shell script `stop_and_clean.sh`.  
Which can be run as follows:
```bash
bash stop_and_clean.sh
```

### In Python
The application can also be run directly in Python. 
For this it is necessary to have a Python 3.10 environment with the libraries in `requirements.txt` installed.  
This can be achieved as follows:
```bash
python3 -m venv fdmp_env

source fdmp_env/bin/activate

pip install -r requirements.txt
```

You can then start the application using the following command:
```bash
python main.py
```

On startup, the application will prompt for any available Vantage6 server credentials and a schema JSON file.  
This will appear as follows:
```python
# "Please provide the path to the Vantage6 configuration JSON file or press enter to use mock data."
# example_data/demo_network_config.json

# "Please provide the path to the global schema JSON file."
# example_data/schema.json
```

The application should now be running and available on `http://localhost:8050`.

## Example data
The application comes with example data in the `example_data/` directory.
This data consists of the following:
- `demo_network_config.json`: 
Example Vantage6 server credentials that can directly be used with Vantage6's developer network 
(you can set this up through `v6 dev create-demo-network` and `v6 dev start-demo-network` respectively)
- `mockresult.json`: This file contains mock data retrieved through a task using the 
described Vantage6 algorithm and Vantage6 developer network. 
The annotated data shown in this example was created using the example data in https://github.com/MaastrichtU-CDS/Flyover.
- `schema.json`: This file contains the expected schema of the data that is to be shown in the application. 
This schema was extracted from the example data in https://github.com/MaastrichtU-CDS/Flyover.
