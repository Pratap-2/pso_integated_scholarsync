import os
from dotenv import load_dotenv
from azure.cosmos import CosmosClient, PartitionKey

load_dotenv()

endpoint = os.getenv("COSMOS_ENDPOINT")
key = os.getenv("COSMOS_KEY")

database_name = os.getenv("COSMOS_DATABASE")
container_name = os.getenv("COSMOS_CONTAINER")

client = None
database = None
container = None

def get_container():
    global client, database, container
    if container is None:
        try:
            client = CosmosClient(endpoint, key)
            database = client.create_database_if_not_exists(id=database_name)
            container = database.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path="/session_id")
            )
        except Exception as e:
            print(f"Cosmos DB connection failed: {e}")
    return container