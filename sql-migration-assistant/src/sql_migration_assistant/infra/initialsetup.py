import logging
from typing import Callable
import base64
from pathlib import Path

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
from databricks.sdk.service.catalog import VolumeType
from databricks.sdk.service.workspace import ObjectType, WorkspaceObjectAccessControlRequest, WorkspaceObjectPermissionLevel, ImportFormat, Language
from sql_migration_assistant.utils import logger
from sql_migration_assistant.utils.storage import get_db_connection, execute_query

from databricks.sdk.errors.platform import ResourceAlreadyExists, NotFound
from databricks.sdk.service.vectorsearch import (
    EndpointType,
    DeltaSyncVectorIndexSpecRequest,
    PipelineType,
    EmbeddingSourceColumn,
    VectorIndexType,
)

from .jobs_infra import JobsInfra


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
        self.volume_dirs = {
                "checkpoint": "code_ingestion_checkpoints",
                "input": "input_code",
                "output": "output_code",
            }

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

    def select_only(
        self,
        entity: str,
        list_all: Callable[[], list[str]],
    ) -> str:
        """
        User choose a Entity that can be selected from existing ones
                """
        all_entities = list_all()

        choices = all_entities

        question = f"Choose a {entity}: please enter the number of the {entity} you would like to use."
        choice = self.prompts.choice(question, choices, sort=False)

        return choice


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

        def _create_UC_volume(name):
            self.w.volumes.create(
                name=name,
                catalog_name=self.config.get("CATALOG"),
                schema_name=self.config.get("SCHEMA"),
                comment="Volume for storing assets related to the SQL migration assistant.",
                volume_type=VolumeType.MANAGED,
            )
            for key in self.volume_dirs.keys():
                dir_ = self.volume_dirs[key]
                volume_path = f"/Volumes/{self.config.get('CATALOG')}/{self.config.get('SCHEMA')}/{name}/{dir_}"
                self.w.dbutils.fs.mkdirs(volume_path)

        def _create_tables():
            #TODO move this table name / table schema somewhere else?
            tables = {
                "sql_migration_assistant_code_intent": f"(id BIGINT, code STRING, intent STRING, notebook_url STRING) TBLPROPERTIES (delta.enableChangeDataFeed = true)",
                "bronze_raw_code": f"(path STRING, modificationTime TIMESTAMP, length INT, content STRING,loadDatetime TIMESTAMP)",
                "bronze_prompt_config": f"(promptID INT, agentConfigs MAP <STRING, MAP <STRING, STRING>>, loadDatetime TIMESTAMP)",
                "bronze_holding_table": f"(id LONG, path STRING, modificationTime TIMESTAMP, length INT, content STRING, "
                                        f"loadDatetime TIMESTAMP, promptID INT, "
                                        f"agentConfigs MAP <STRING, MAP <STRING, STRING>>)",
                "silver_llm_responses": f"(path STRING, promptID INT, processedDateString STRING, content STRING, "
                                        f"agentName STRING, agentResponse STRING, outputNotebookPath STRING, "
                                        f"similarCodeNotebooks ARRAY<STRUCT<notebook_url: STRING, intent:STRING, "
                                        f"similarity:DOUBLE>>)",
                "gold_transformed_notebooks": f"(promptID INT, content STRING, processedDateString STRING, notebookAsString STRING, "
                                              f"outputVolumePath STRING, outputNotebookPath STRING, "
                                              f"similarCodeNotebooks ARRAY<STRUCT<notebook_url: STRING, intent:STRING, similarity:DOUBLE>>, "
                                              f"agentResponses MAP<STRING,STRING>)",
            }
            for table_name, table_spec in tables.items():
                self.w.statement_execution.execute_statement(
                    statement=f"CREATE TABLE IF NOT EXISTS `{table_name}` {table_spec}"
                    ,catalog=self.config.get('CATALOG')
                    ,schema=self.config.get('SCHEMA')
                    ,warehouse_id=self.config.get('WAREHOUSE_ID')
                )

        def _list_catalogs():
            return [x.name for x in self.w.catalogs.list()]

        def _list_schema():
            return [x.name for x in self.w.schemas.list(self.config.get("CATALOG"))]

        def _list_volumes():
            return [x.name for x in self.w.volumes.list(catalog_name=self.config.get("CATALOG"), schema_name=self.config.get("SCHEMA"))]


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

        volume = self.create_or_select(
            "volume",
            _list_volumes,
            create=_create_UC_volume,
            default="sql_migration_assistant_volume",
        )
        self.config["VOLUME_NAME"] = volume
        for key in self.volume_dirs.keys():
            dir_ = self.volume_dirs[key]
            volume_path = f"/Volumes/{self.config.get('CATALOG')}/{self.config.get('SCHEMA')}/{volume}/{dir_}"
            self.config[f"VOLUME_NAME_{key.upper()}_PATH"] = volume_path

        # TODO - this shouldnt be hardcoded, but should be a part of the config
        _create_tables()
        self.config["CODE_INTENT_TABLE_NAME"] = "sql_migration_assistant_code_intent"
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

    @_handle_errors
    def setup_vector_search(self):

        def _create_VS_endpoint(name):
            self.w.vector_search_endpoints.create_endpoint(
                name=name,
                endpoint_type=EndpointType.STANDARD,
            )

        def _create_VS_index():
            try:
                self.w.vector_search_indexes.create_index(
                    name=f'{self.config.get("CATALOG")}.{self.config.get("SCHEMA")}.{self.config.get("VS_INDEX_NAME")}',
                    endpoint_name=self.config.get("VS_ENDPOINT_NAME"),
                    primary_key="id",
                    index_type=VectorIndexType.DELTA_SYNC,
                    delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
                        source_table=f'{self.config.get("CATALOG")}.{self.config.get("SCHEMA")}.{self.config.get("CODE_INTENT_TABLE_NAME")}',
                        pipeline_type=PipelineType.TRIGGERED,
                        embedding_source_columns=[
                            EmbeddingSourceColumn(
                                embedding_model_endpoint_name=self.config.get("EMBEDDING_MODEL_ENDPOINT"),
                                name="intent",
                            )
                        ]
                    ),
                )
            except ResourceAlreadyExists as e:
                logging.info(
                    f"Index {self.config.get('VS_INDEX_NAME')} already exists. Using existing index."
                )
            except Exception as e:
                raise e

        def _list_vs_endpoints():
            all_endpoints = list(self.w.vector_search_endpoints.list_endpoints())
            available_endpoints = [x.name for x in all_endpoints if x.num_indexes < 50]
            return available_endpoints

        def _list_embedding_models():
            return [e.name for e in self.w.serving_endpoints.list() if e.task and "embedding" in e.task]

        endpoint = self.create_or_select(
            entity="Vector Search endpoint with less than 50 indices",
            list_all=_list_vs_endpoints,
            create=_create_VS_endpoint,
            default="sql_migration_assistant_vs_endpoint",
        )
        self.config["VS_ENDPOINT_NAME"] = endpoint

        embedding_model = self.select_only(
            entity="Embedding Model",
            list_all=_list_embedding_models
        )
        self.config["EMBEDDING_MODEL_ENDPOINT"] = embedding_model

        self.config["VS_INDEX_NAME"]= "sql_migration_assistant_code_intent_vs_index"
        _create_VS_index()

    @_handle_errors
    def _set_permissions(self):
        # give app SP permissions on warehouse
        try:
            self.w.warehouses.update_permissions(
                self.warehouse.id,
                access_control_list=[
                    WarehouseAccessControlRequest(
                        service_principal_name=self.app.service_principal_client_id,
                        permission_level=WarehousePermissionLevel.CAN_USE,
                    ),
                ],
            )
        except Exception as e:
            logger.warning(
                f"Could not set permissions for warehouse {self.warehouse.name}: and service_principal {self.app.service_principal_name}"
            )
            logger.warning(e)
        # give app SP permissions on catalog
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
        # give app SP permissions on schema
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
            logger.warning(e)


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

        self.w.workspace.mkdirs(deployment_path)

        # give app SP permissions on workspace location
        try:
            directory = self.w.workspace.get_status(self.config.get("DEPLOYMENT_PATH"))
            self.w.workspace.update_permissions(
                workspace_object_type="directories", #directory.object_type, ObjectType.DIRECTORY# incorrect docs again
                workspace_object_id=str(directory.object_id),
                access_control_list=[
                    WorkspaceObjectAccessControlRequest(
                        service_principal_name=self.app.service_principal_client_id,
                        permission_level=WorkspaceObjectPermissionLevel.CAN_MANAGE,
                    )
                ],
            )
        except Exception as e:
            logger.warning(
                f"Could not set permissions for Directory {self.config.get('DEPLOYMENT_PATH')}: and service_principal {self.app.service_principal_name}"
            )
            logger.warning(e)

    @_handle_errors
    def setup_job(self):
        job_infra = JobsInfra(self.config, self.w)
        jobs_path = self.config["DEPLOYMENT_PATH"]+"/jobs/"
        self.w.workspace.mkdirs(jobs_path)
        file_root=Path(__file__).parent.parent.parent.parent.resolve()/"jobs"
        files = ['bronze_to_silver.py', 'call_agents.py', 'silver_to_gold.py']
        for f in files:
            full_path = file_root/f
            with open(full_path, "r") as _:
                content=_.read()
            self.w.workspace.import_(
                content=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
                path=jobs_path+f,
                format=ImportFormat.SOURCE,
                language=Language.PYTHON
            )

        # create job and get job id
        self.config["TRANSFORMATION_JOB_ID"] = job_infra.create_transformation_job()

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

        logging.info("Setting up Vector Search infrastructure")
        print("\nSetting up Vector Search infrastructure")
        self.setup_vector_search()

        ############################################################
        logging.info("Setting up Databricks App")
        print("\nSetting up Databricks App")
        self.setup_app()

        ############################################################
        logging.info("Setting up Deployment Directory")
        print("\nSetting up Deployment Directory")
        self.setup_deployment_dir()

        ############################################################
        logging.info("Setting up Job")
        print("\nSetting up Job")
        self.setup_job()

        ############################################################
        logging.info("Infrastructure setup complete")
        print("\nInfrastructure setup complete")

        return self.config
