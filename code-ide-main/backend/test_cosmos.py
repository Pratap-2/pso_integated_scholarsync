from app.services.cosmos_services import get_container

if __name__ == "__main__":
    try:
        container = get_container()
        print("Successfully connected to Cosmos DB container:", container.id)
    except Exception as e:
        print("Error connecting to Cosmos DB:", e)
