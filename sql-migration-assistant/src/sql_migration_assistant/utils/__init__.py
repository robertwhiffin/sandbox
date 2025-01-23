import logging
from logging import StreamHandler

from databricks.sdk import WorkspaceClient
from databricks.sdk.config import Config
from sql_migration_assistant.version import __version__

logger = logging.getLogger("sql_migration_assistant")
logger.setLevel(logging.INFO)
logger.addHandler(StreamHandler())


def get_workspace_client(profile: str) -> WorkspaceClient:
    return WorkspaceClient(
        product="sql_migration_assistant", product_version=__version__, profile=profile
    )
