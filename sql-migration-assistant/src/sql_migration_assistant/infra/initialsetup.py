import logging
from typing import Callable

from databricks.labs.blueprint.tui import Prompts
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import ResourceAlreadyExists, BadRequest
from databricks.sdk.errors.platform import PermissionDenied
from databricks.sdk.service.apps import App
from databricks.sdk.service.sql import (
    CreateWarehouseRequestWarehouseType,
    WarehouseAccessControlRequest,
    WarehousePermissionLevel,
)

from sql_migration_assistant.utils import logger, get_db_connection


# this is a decorator to handle errors and do a retry where user is asked to choose an existing resource
def _handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PermissionDenied:
            logging.error(
                "You do not have permission to create the requested resource. Please ask your admin to grant"
                " you permission or choose an existing resource."
            )
            return func(*args, **kwargs)
        except ResourceAlreadyExists:
            logging.error(
                "Resource already exists. Please choose an alternative resource."
            )
            return func(*args, **kwargs)
        except BadRequest as e:
            if "Cannot write secrets" in str(e):
                logging.error(
                    "Cannot write secrets to Azure KeyVault-backed scope. Please choose an alternative "
                    "secret scope."
                )
                return func(*args, **kwargs)
            else:
                raise e

    return wrapper


class SetUpMigrationAssistant:
    def __init__(self, workspace_client: WorkspaceClient, p: Prompts):
        self.app = None
        self.w = workspace_client
        self.config = {}
        self.prompts = p
        self.warehouse = None

    def create_or_select(
        self,
        entity: str,
        list_all: Callable[[], list[str]],
        create: Callable[[str], None],
        default: str,
    ) -> str:
        """
        User choose a Entity that can be selected from existing ones or created new
        """
        create_new = (
            self.prompts.choice(
                f"Create a new {entity} or use existing?",
                ["Create new", "Use existing"],
            )
            == "Create new"
        )
        if not create_new:
            all_entities = list_all()

            choices = all_entities + ["Create a new one"]

            question = f"Choose a {entity}: please enter the number of the {entity} you would like to use."
            choice = self.prompts.choice(question, choices, sort=False)

            if "Create a new one" in choice:
                create_new = True
            else:
                return choice
        if create_new:
            new_name = self.prompts.question(f"Choose a {entity} name", default=default)

            print(f"Creating a new {entity} {new_name}.")
            create(new_name)
            return new_name

    @_handle_errors
    def setup_warehouse(self):
        """
        User choose a warehouse which will be used for all migration assistant operations
        """

        def create(name: str):
            self.w.warehouses.create_and_wait(
                name=name,
                cluster_size="2X-Small",
                max_num_clusters=1,
                enable_serverless_compute=True,
                enable_photon=True,
                warehouse_type=CreateWarehouseRequestWarehouseType.PRO,
                auto_stop_mins=5,
            )

        def list_all():
            return [x.name for x in self.w.warehouses.list()]

        warehouse_name = self.create_or_select(
            entity="warehouse",
            list_all=list_all,
            create=create,
            default="sql_migration_assistant",
        )
        self.warehouse = [
            x for x in self.w.warehouses.list() if x.name == warehouse_name
        ][0]

        # update config with user choice
        self.config["WAREHOUSE_ID"] = self.warehouse.id

    @_handle_errors
    def setup_unity(self):
        def _create_UC_catalog(name: str):
            """Create a new Unity Catalog."""
            self.w.catalogs.create(
                name=name,
                comment="Catalog for storing assets related to the SQL migration assistant.",
            )

        def _create_UC_schema(name: str):
            """Create a new Unity Schema."""
            self.w.schemas.create(
                name=name,
                catalog_name=self.config.get("CATALOG"),
                comment="Schema for storing assets related to the SQL migration assistant.",
            )

        def _list_catalogs():
            return [x.name for x in self.w.catalogs.list()]

        def _list_schema():
            return [x.name for x in self.w.schemas.list(self.config.get("CATALOG"))]

        catalog = self.create_or_select(
            "catalog",
            _list_catalogs,
            create=_create_UC_catalog,
            default="sql_migration_assistant",
        )
        self.config["CATALOG"] = catalog

        schema = self.create_or_select(
            "schema",
            _list_schema,
            create=_create_UC_schema,
            default="sql_migration_assistant",
        )
        self.config["SCHEMA"] = schema

    @_handle_errors
    def setup_app(self):
        def create(name: str):
            print("Creating new app")
            self.w.apps.create_and_wait(app=App(name))
            print("Created new app")

        def list_all():
            return [x.name for x in self.w.apps.list()]

        app_name = self.create_or_select(
            entity="app",
            list_all=list_all,
            create=create,
            default="sql-migration-assistant",
        )
        self.config["APP"] = app_name
        self.app = self.w.apps.get(app_name)
        self._set_permissions()

    def _set_permissions(self):
        try:
            self.w.warehouses.update_permissions(
                self.warehouse.id,
                access_control_list=[
                    *self.w.warehouses.get_permissions(
                        self.warehouse.id
                    ).access_control_list,
                    WarehouseAccessControlRequest(
                        service_principal_name=app.service_principal_name,
                        permission_level=WarehousePermissionLevel.CAN_USE,
                    ),
                ],
            )
        except Exception as e:
            logger.warning(
                f"Could not set permissions for warehouse {self.warehouse.name}: and service_principal {self.app.service_principal_name}"
            )
        try:
            con = get_db_connection(self.w.config.profile, self.warehouse.id)
            cursor = con.cursor()
            cursor.execute(
                f"GRANT USE CATALOG ON CATALOG {self.config.get('CATALOG')} TO `{self.app.service_principal_client_id}`"
            )
            cursor.close()
        except Exception as e:
            logger.warning(
                f"Could not set permissions for Catalog {self.config.get('CATALOG')}: and service_principal {self.app.service_principal_name}"
            )
        try:
            con = get_db_connection(self.w.config.profile, self.warehouse.id)
            cursor = con.cursor()
            cursor.execute(
                f"GRANT ALL PRIVILEGES ON SCHEMA {self.config.get('CATALOG')}.{self.config.get('SCHEMA')} TO `{self.app.service_principal_client_id}`"
            )
            cursor.close()
        except Exception as e:
            logger.warning(
                f"Could not set permissions for Schema {self.config.get('CATALOG')}.{self.config.get('SCHEMA')}: and service_principal {self.app.service_principal_name}"
            )

    @_handle_errors
    def setup_deployment_dir(self):
        if self.app.default_source_code_path == "":
            deployment_path = self.prompts.question(
                "Choose a workspace directory to deploy the code",
                default=f"/Workspace/Users/{self.w.current_user.me().user_name}/sql_migration_assistant",
            )
        else:
            deployment_path = self.app.default_source_code_path
        self.config["DEPLOYMENT_PATH"] = deployment_path

    def setup_migration_assistant(self):
        logging.info("Setting up infrastructure")
        print("\nSetting up infrastructure")

        ############################################################
        print(
            "\n***Choose a Databricks SQL Warehouse***\n"
            "This warehouse will be used for all migration assistant operations, setup and ongoing."
        )

        self.setup_warehouse()

        ############################################################
        logging.info("Setting up Unity Catalog infrastructure")
        print("\nSetting up Unity Catalog infrastructure")
        self.setup_unity()

        ############################################################
        logging.info("Setting up Databricks App")
        print("\nSetting up Databricks App")
        self.setup_app()

        ############################################################
        logging.info("Setting up Deployment Directory")
        print("\nSetting up Deployment Directory")
        self.setup_deployment_dir()

        ############################################################
        logging.info("Infrastructure setup complete")
        print("\nInfrastructure setup complete")

        return self.config
