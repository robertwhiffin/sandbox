import logging
import sys
from importlib.metadata import version
from logging import StreamHandler

from databricks.sdk import WorkspaceClient

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
