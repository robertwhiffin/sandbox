import logging
from logging import StreamHandler

from databricks.sdk import WorkspaceClient

logger = logging.getLogger("sql_migration_assistant")
logger.setLevel(logging.INFO)
logger.addHandler(StreamHandler())


def get_workspace_client(profile: str) -> WorkspaceClient:
    return WorkspaceClient(
        product="sql_migration_assistant", product_version="0.0.1", profile=profile
    )


