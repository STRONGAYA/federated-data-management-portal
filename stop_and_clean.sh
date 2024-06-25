#!/bin/bash

# Remove the stack
docker stack rm federated-data-management

# Remove the schema
rm -f federated-data-management-portal/schema.json

# Remove the Docker secrets
echo "Removing the following Docker secrets"
docker secret rm vantage6_service_username
docker secret rm vantage6_service_password
docker secret rm vantage6_server_url
docker secret rm vantage6_server_port
docker secret rm vantage6_server_api
docker secret rm vantage6_private_key_path
docker secret rm vantage6_collaboration
docker secret rm vantage6_aggregating_organisation