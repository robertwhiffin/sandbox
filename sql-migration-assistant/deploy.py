import os
import subprocess
from importlib.metadata import version
from pathlib import Path

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.apps import App, AppDeployment
from databricks.sdk.service.sql import (
    WarehouseAccessControlRequest,
    WarehousePermissionLevel,
)

from sql_migration_assistant.utils import logger, get_db_connection

import argparse


def main(profile, project_dir, config_path):
    """
    Main function to handle the deployment.

    Parameters:
    - profile (str): The name of the profile.
    - project_dir (str): The directory of the project.
    - config_path (str): The path to the configuration file.
    """
    check_profile(profile)
    project_dir_resolved = os.path.realpath(project_dir)
    config_path_resolved = os.path.realpath(config_path)
    print(f"Profile: {profile}")
    print(f"Project Directory: {project_dir_resolved}")
    print(f"Config Path: {config_path_resolved}")

    with open(config_path_resolved, "r") as config_file:
        config = yaml.safe_load(config_file)

    create_app_yml(config)

    w = WorkspaceClient(profile=profile, product="sql_migration_assistant", product_version=version("sql_migration_assistant"))
    warehouses = [
        w for w in w.warehouses.list() if w.name == config.get("SQL_WAREHOUSE_NAME")
    ]
    if len(warehouses) == 0:
        logger.warning(f"Warehouse not found: {config.get('SQL_WAREHOUSE_NAME')}")
        warehouse = None
    else:
        warehouse = warehouses[0]

    try:
        app = w.apps.get(config.get("APP_NAME"))
    except NotFound:
        print("Creating new app")
        app = w.apps.create_and_wait(app=App(config.get("APP_NAME")))
        print("Created new app")
        try:
            w.warehouses.update_permissions(
                warehouse.id,
                access_control_list=[
                    *w.warehouses.get_permissions(warehouse.id).access_control_list,
                    WarehouseAccessControlRequest(
                        service_principal_name=app.service_principal_name,
                        permission_level=WarehousePermissionLevel.CAN_USE,
                    )
                ],
            )
        except Exception as e:
            logger.warning(
                f"Could not set permissions for warehouse {warehouse.name}: and service_principal {app.service_principal_name}"
            )
        try:
            con = get_db_connection(profile, warehouse.id)
            cursor = con.cursor()
            cursor.execute(
                f"GRANT ALL PRIVILEGES ON SCHEMA {config.get('CATALOG')}.{config.get('SCHEMA')} TO `{app.service_principal_client_id}`"
            )
            cursor.close()
        except Exception as e:
            logger.warning(
                f"Could not set permissions for Schema {config.get('CATALOG')}.{config.get('SCHEMA')}: and service_principal {app.service_principal_name}"
            )

    print("Syncing files to workspace")
    if app.default_source_code_path == "":
        deployment_path = config.get("DEPLOYMENT_PATH")
    else:
        deployment_path = app.default_source_code_path

    subprocess.run(
        [
            "databricks",
            "sync",
            project_dir_resolved,
            deployment_path,
            "--profile",
            profile,
        ]
    )

    print("Deploying app")
    deployment = w.apps.deploy_and_wait(
        app.name, app_deployment=AppDeployment(source_code_path=deployment_path)
    )
    print(f"App deployed. URL: {app.url} with result {deployment.status}")


def create_app_yml(config):
    content = {
        "command": ["python", "src/sql_migration_assistant/main.py"],
        "env": [{"name": key, "value": value} for key, value in config.items()],
    }
    with open("app.yml", "w") as file:
        yaml.dump(content, file)

def check_profile(profile):
    if profile is None:
        print("Profile not specified, defaulting to DEFAULT")
    try:
        WorkspaceClient(profile=profile)
    except ValueError:
        raise Exception("The databricks cli is not configured yet. Please run 'databricks configure'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A CLI for managing projects with profiles and configuration files."
    )

    # Adding arguments
    parser.add_argument(
        "--profile", type=str, required=False, help="The profile name to use.", default=None
    )
    parser.add_argument(
        "--project-dir", type=str, required=False, help="The project directory.", default=os.getcwd()
    )
    parser.add_argument(
        "--config-path",
        type=str,
        required=False,
        help="The path to the configuration file.",
        default=Path(os.getcwd(), "config.yml"),
    )

    # Parse the arguments
    args = parser.parse_args()

    # Call the main function with the parsed arguments
    main(args.profile, args.project_dir, args.config_path)
