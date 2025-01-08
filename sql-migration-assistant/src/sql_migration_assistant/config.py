import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

import yaml

from sql_migration_assistant.utils.runindatabricks import current_folder

FOUNDATION_MODEL_NAME = os.environ.get("SERVED_FOUNDATION_MODEL_NAME")
SQL_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")
VECTOR_SEARCH_ENDPOINT_NAME = os.environ.get("VECTOR_SEARCH_ENDPOINT_NAME")
VS_INDEX_NAME = os.environ.get("VS_INDEX_NAME")
CODE_INTENT_TABLE_NAME = os.environ.get("CODE_INTENT_TABLE_NAME")
CATALOG = os.environ.get("CATALOG", "sebastian_grunwald")
SCHEMA = os.environ.get("SCHEMA")
VOLUME_NAME = os.environ.get("VOLUME_NAME")
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
TRANSFORMATION_JOB_ID = os.environ.get("TRANSFORMATION_JOB_ID")
WORKSPACE_LOCATION = os.environ.get("WORKSPACE_LOCATION")
VOLUME_NAME_INPUT_PATH = os.environ.get("VOLUME_NAME_INPUT_PATH")
PROMPT_HISTORY_TABLE_NAME = os.environ.get("PROMPT_HISTORY_TABLE_NAME")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
SECRET_KEY = os.environ.get("SECRET_KEY")
SECRET_SCOPE = os.environ.get("SECRET_SCOPE")
EMBEDDING_ENDPOINT = os.environ.get("EMBEDDING_ENDPOINT")


yaml_path = Path(__file__).parent.parent.parent.resolve() / "config.yaml"


class Config:
    config: dict = {}
    

    def from_yaml(self):
        with open(yaml_path, "r") as f:
            content = yaml.safe_load(f)
        self.config = {**self.config, **content}

    def set_config(self, key, value):
        self.config[key] = value

    def to_yaml(self):
        with open(yaml_path, "w") as f:
            yaml.safe_dump(self.config, f)

