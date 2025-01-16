import os
from pathlib import Path

import pandas as pd
import yaml
from databricks.sdk.errors import NotFound

from sql_migration_assistant.utils import (
    get_workspace_client,
    logger,
)
from sql_migration_assistant.utils.storage import get_db_connection, table_exists, create_table, insert, read

yaml_path = Path(__file__).parent.parent.parent.resolve() / "config.yml"


class Config:
    config: dict = {
        "PROMPT_TABLE": "sql_migration_assistant_prompts",
        "CONFIG_TABLE_NAME": "sql_migration_assistant_configs",
        "CODE_INTENT_TABLE_NAME": "sql_migration_assistant_code_intent",
        "VS_INDEX_NAME": "sql_migration_assistant_code_intent_vs_index",
        "INSTRUCTIONS_TABLE_NAME": "sql_migration_assistant_instructions",
    }

    def __init__(self, profile=None):
        self.from_environ()
        self.profile = (
            os.environ.get("DATABRICKS_PROFILE") if profile is None else profile
        )
        self.w = get_workspace_client(self.profile)
        self.catalog = self.config.get("CATALOG")
        self.schema = f"{self.catalog}.{self.config.get('SCHEMA')}"
        self.config_table = self.config.get('CONFIG_TABLE_NAME')
        self.validate_first_setup()
        self.con = get_db_connection(self.profile, self.warehouse.id)
        self.from_sql()

    def get_workspace_path(self):
        return self.config.get(
            "WORKSPACE_PATH",
            f"/Workspace/Users/{self.w.config.username}/sql_migration_assistant_files",
        )

    def from_sql(self):
        if not table_exists(self.config_table, self):
            logger.warning(
                f"No Config table found at {self.config_table}. Creating new one"
            )
            create_table(self.config_table, "key STRING, value STRING", config)
            insert(self.config_table, [{"key": k, "value": v} for k,v in self.config.items()],self)
        else:
            config = read(self.config_table, self)
            for _, row in config.iterrows():
                self.config[row["key"]] = row["value"]

    def from_environ(self):
        for key in ["CATALOG", "SCHEMA", "SQL_WAREHOUSE_NAME"]:
            self.config[key] = os.environ.get(key)

    def from_yaml(self):
        with open(yaml_path, "r") as f:
            content = yaml.safe_load(f)
        self.config = {**self.config, **content}

    def set_config(self, key, value):
        logger.info(f"Setting Config {key} to {value}")
        self.set_configs({key: value})

    def set_configs(self, configs: dict):
        logger.info(f"Setting Configs {configs}")
        insert(self.config_table, [{"key": k, "value": v} for k,v in configs.items()], self, keys=["key"], upsert=True)
        self.config = {**self.config, **configs}

    def get(self, key, default=None):
        return self.config.get(key, default)

    def validate_key_exists(self, key) -> list[str]:
        if key not in self.config:
            return [
                f"{key} not found in config.yml, please configure it before deployment"
            ]
        return []

    def validate_first_setup(self):
        """Validate the initial configuration"""
        errors = []
        for k in ["CATALOG", "SCHEMA", "SQL_WAREHOUSE_NAME"]:
            errors.extend(self.validate_key_exists(k))

        if self.config.get("DEPLOYMENT_MODE") == "app":
            errors.extend(self.validate_key_exists("APP_NAME"))

        try:
            self.w.catalogs.get(self.catalog)
        except NotFound:
            errors.append(
                f"Catalog {self.catalog} does not exist. Please create it before deployment"
            )
        try:
            self.w.schemas.get(self.schema)
        except NotFound:
            errors.append(
                f"Schema {self.schema} does not exist. Please create it before deployment"
            )

        warehouses = [
            w
            for w in self.w.warehouses.list()
            if w.name == self.config.get("SQL_WAREHOUSE_NAME")
        ]
        if len(warehouses) == 0:
            errors.append(
                f"Warehouse {self.config.get('SQL_WAREHOUSE_NAME')} found. Please create it before deployment"
            )
        else:
            self.warehouse = warehouses[0]
        if len(errors) > 0:
            raise Exception(
                f"Initial Configuration not valid. Please fix the following errors:"
                "\n".join(errors)
            )
        logger.info("Initial Configuration validated")

    def initial_setup_done(self) -> bool:
        """
        Tests if the app was already initialized.
        """
        return (
            len(
                {
                    "EMBEDDING_MODEL_ENDPOINT",
                    "VECTOR_SEARCH_ENDPOINT_NAME",
                    "VOLUME",
                }.difference(self.config.keys())
            )
            == 0
        )


config = None


def get_config(profile=None):
    global config
    config = Config(profile) if config is None else config
    return config
