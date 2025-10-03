
from typing import Any, Dict, Optional, List
import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential

DB_NAME = os.getenv("COSMOS_DB", "fantasy_helper")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")

# Use Managed Identity in production, key in local dev
if COSMOS_ENDPOINT and COSMOS_KEY:
    _client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
elif COSMOS_ENDPOINT:
    # Production: use Managed Identity
    credential = DefaultAzureCredential()
    _client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
else:
    _client = None

_db = _client.get_database_client(DB_NAME) if _client else None

def _container(name: str):
    assert _db is not None, "Cosmos not configured"
    try:
        return _db.get_container_client(name)
    except Exception:
        _db.create_container_if_not_exists(id=name, partition_key=PartitionKey(path="/partitionKey"))
        return _db.get_container_client(name)

def upsert(container: str, doc: Dict[str, Any], partition: str):
    c = _container(container)
    doc["partitionKey"] = partition
    return c.upsert_item(doc)

def get_by_id(container: str, id: str, partition: str) -> Optional[Dict[str, Any]]:
    c = _container(container)
    try:
        return c.read_item(item=id, partition_key=partition)
    except Exception:
        return None

def query(container: str, query: str, params: Optional[List[Dict[str, Any]]] = None):
    c = _container(container)
    return list(c.query_items(query=query, parameters=params or [], enable_cross_partition_query=True))
