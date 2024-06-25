#!/bin/bash

echo "Welcome to a federated data management portal designed for Vantage6."
echo "You are now going to create the Docker secrets for the service account and the server configuration."

# Check if Docker is running in swarm mode, if not, initialize Docker Swarm
docker info | grep Swarm: | grep inactive > /dev/null
if [ $? -eq 0 ]; then
  echo "Docker Swarm is not initialized, initializing now..."
  docker swarm init
fi

echo "Please enter the username of the service account:"
read username
echo "$username" | docker secret create vantage6_service_username -

echo "Please enter the password of the service account:"
read -s password
echo "$password" | docker secret create vantage6_service_password -

echo "Please enter the server URL:"
read -r server_url
echo "$server_url" | docker secret create vantage6_server_url -

echo "Please enter the server port:"
read server_port
echo "$server_port" | docker secret create vantage6_server_port -

echo "Please enter the server API path:"
read -r server_api
echo "$server_api" | docker secret create vantage6_server_api -

echo "Please enter the collaboration id:"
read -r collaboration_id
echo "$collaboration_id" | docker secret create vantage6_collaboration -

echo "Please enter the path to the private key in case encryption is enabled for this collaboration:"
read -r private_key_path
echo "$private_key_path" | docker secret create vantage6_private_key_path -

echo "Please enter the id of the aggregating organisation:"
read aggregator_id
echo "$aggregator_id" | docker secret create vantage6_aggregating_organisation -

echo "Please enter the path to the schema JSON file:"
read -r json_file_path
export JSON_FILE_PATH=$json_file_path

docker build -t fdmp_image .

docker stack deploy --compose-file docker-compose.yml federated-data-management

echo "The federated data management portal should now be running."
read -p "Press enter to exit"