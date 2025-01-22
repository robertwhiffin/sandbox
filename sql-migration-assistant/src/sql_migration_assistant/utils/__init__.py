import logging
import sys
from logging import StreamHandler

from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.config import Config
from importlib.metadata import version

logger = logging.getLogger("sql_migration_assistant")
logger.setLevel(logging.INFO)
console_handler = StreamHandler(sys.stdout)
console_handler.setFormatter(
    logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
)
logger.addHandler(console_handler)


def get_workspace_client(profile: str) -> WorkspaceClient:
    return WorkspaceClient(
        product="sql_migration_assistant",
        product_version=version("sql_migration_assistant"),
        profile=profile,
    )


def get_db_connection(profile: str, warehouse_id: str):
    cfg = Config(profile=profile)

    con = sql.connect(
        server_hostname=cfg.host,
        credentials_provider=lambda: cfg.authenticate,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
    )
    return con
