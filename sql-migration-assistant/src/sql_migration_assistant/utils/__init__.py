import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.config import Config
from databricks import sql

logger = logging.getLogger("sql_migration_assistant")
logger.setLevel(logging.INFO)
def get_workspace_client(profile: str) -> WorkspaceClient:
    return WorkspaceClient(product="sql_migration_assistant", product_version="0.0.1", profile=profile)

def get_db_connection(profile: str, warehouse_id: str):
    cfg = Config(profile=profile)

    con = sql.connect(server_hostname=cfg.host, credentials_provider=lambda: cfg.authenticate,
                      http_path=f"/sql/1.0/warehouses/{warehouse_id}")
    return con

