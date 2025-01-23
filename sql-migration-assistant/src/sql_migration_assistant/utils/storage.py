from typing import Any

import pandas as pd
from databricks import sql
from databricks.sdk.config import Config
from databricks.sdk.errors import NotFound

from sql_migration_assistant.utils import logger


def ensure_config(func):
    def wrapper(*args, **kwargs):
        if "config" not in kwargs or kwargs["config"] is None:
            from sql_migration_assistant.config import get_config

            kwargs["config"] = get_config()
        return func(*args, **kwargs)

    return wrapper


@ensure_config
def read(
    table: str, config=None, columns: list[str] = None, where: str = None
) -> pd.DataFrame:
    select_clause = "*" if columns is None else ",".join(columns)
    where_clause = "" if where is None else f" WHERE {where}"
    return pd.read_sql_query(
        f"SELECT {select_clause} FROM {config.schema}.{table}{where_clause}", config.con
    )


@ensure_config
def construct_upsert_query(
    table: str,
    values: list[dict[str, Any]],
    keys: list[str],
    columns: list[str],
    config,
) -> str:
    if keys is None:
        raise ValueError("Keys need to be specified for upserting")
    where_clause = " and ".join(
        [
            f"""{key} in  ('{"','".join(set([v[key] for v in values]))}')"""
            for key in keys
        ]
    )
    logger.debug(f"Upserting, where clause: {where_clause}")
    values_clause = ",".join(
        [f"""('{"','".join([str(row[c]) for c in columns])}')""" for row in values]
    )
    logger.debug(f"Upserting, value clause: {values_clause}")
    query = f"INSERT INTO {config.schema}.{table} REPLACE WHERE {where_clause} VALUES {values_clause}"
    logger.debug(f"Upserting, query: {query}")
    return query


@ensure_config
def construct_insert_query(
    table: str, values: list[dict[str, Any]], config=None
) -> str:
    values_clause = ",".join(
        [f"""('{"','".join([v for v in row.values()])}')""" for row in values]
    )
    query = f"INSERT INTO {config.schema}.{table} ({','.join(values[0].keys())}) VALUES {values_clause}"
    logger.debug(f"Inserting, query: {query}")
    return query


@ensure_config
def execute_query(query: str, config=None):
    cur = config.con.cursor()
    try:
        cur.execute(query)
        logger.info(f"Executed query: {query}")
    except Exception as e:
        logger.error(f"Execution of query failed: {query} with error: {e}")
    cur.close()


@ensure_config
def insert(
    table: str,
    values: list[dict[str, Any]],
    config=None,
    keys: list[str] = None,
    upsert: bool = False,
):
    if upsert:
        # Get column order of base table
        columns = [
            c.name for c in config.w.tables.get(f"{config.schema}.{table}").columns
        ]
        # check if all columns are present
        if set(columns) != set(values[0].keys()):
            raise ValueError("All columns need to be specified for upserting")
        query = construct_upsert_query(table, values, keys, columns, config=config)
    else:
        query = construct_insert_query(table, values, config, config=config)
    execute_query(query, config=config)


@ensure_config
def table_exists(table: str, config=None) -> bool:
    try:
        config.w.tables.get(f"{config.schema}.{table}")
        return True
    except NotFound:
        return False


@ensure_config
def create_table(table: str, schema: str, config=None):
    execute_query(f"Create table {config.schema}.{table} ({schema});", config=config)


@ensure_config
def create_if_not_exists(table: str, schema: str, config=None):
    if not table_exists(table, config=config):
        logger.info(f"Table {table} does not exist")
        create_table(table, schema, config=config)


def get_db_connection(profile: str, warehouse_id: str):
    cfg = Config(profile=profile)

    con = sql.connect(
        server_hostname=cfg.host,
        credentials_provider=lambda: cfg.authenticate,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
    )
    return con
