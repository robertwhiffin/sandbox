import gradio as gr
from databricks.sdk import WorkspaceClient
from tomlkit import value

import sql_migration_assistant.config as config


class ConfigTab:
    header: gr.Markdown
    tab: gr.Tab

    w = WorkspaceClient(profile="demo-east")

    pay_per_token_models = [
        "databricks-meta-llama-3-1-405b-instruct",
        "databricks-meta-llama-3-1-70b-instruct",
        "databricks-dbrx-instruct",
        "databricks-mixtral-8x7b-instruct",
    ]

    def __init__(self):
        with gr.Tab(label="Configuration") as tab:
            self.header = gr.Markdown("Configuration options ")
            catalogs = [c.name for c in self.w.catalogs.list()]
            catalog = gr.Dropdown(
                choices=catalogs,
                label="Catalog",
                filterable=True,
                interactive=True,
                value=config.CATALOG,
            )

            def get_schema(catalog_name):
                try:
                    schemas = [
                        c.name for c in self.w.schemas.list(catalog_name=catalog_name)
                    ]
                except Exception as e:
                    schemas = ["Please select a valid catalog"]
                return gr.Dropdown(
                    schemas, label="Schema", interactive=True, value=config.SCHEMA
                )

            schema = get_schema(catalog.value)
            catalog.select(get_schema, inputs=catalog, outputs=schema)

            secret_scope = gr.Dropdown(
                choices=[s.name for s in self.w.secrets.list_scopes()],
                label="Secret scope",
                interactive=True,
                value=config.SECRET_SCOPE,
            )

            def get_secret_dropdown(secret_scope_name):
                try:
                    secrets = [
                        s.key for s in self.w.secrets.list_secrets(secret_scope_name)
                    ]
                except Exception as e:
                    secrets = ["Please select a valid secret scope"]
                return gr.Dropdown(
                    choices=secrets,
                    label="Secret",
                    interactive=True,
                    value=config.SECRET_KEY,
                )

            secret_dropdown = get_secret_dropdown(secret_scope.value)
            secret_scope.select(
                get_secret_dropdown, inputs=secret_scope, outputs=secret_dropdown
            )

            warehouse_dropdown = gr.Dropdown(
                choices=[w.name for w in self.w.warehouses.list()],
                label="Warehouse",
                interactive=True,
                value=self.get_warehouse_name_by_id(config.SQL_WAREHOUSE_ID),
            )

            embedding_model_endpoint_dropdown = gr.Dropdown(
                choices=[
                    e.name
                    for e in self.w.serving_endpoints.list()
                    if e.task and "embedding" in e.task
                ],
                label="Embedding Endpoint",
                interactive=True,
                value=config.EMBEDDING_ENDPOINT,
            )

            foundation_model_dropdown = gr.Dropdown(
                choices=[
                    ("" if e.name not in self.pay_per_token_models else "PPT - ")
                    + e.name
                    for e in self.w.serving_endpoints.list()
                    if e.name
                ],
                label="Foundation Endpoint",
                interactive=True,
                value=config.FOUNDATION_MODEL_NAME,
            )

            vector_search_dropdown = gr.Dropdown(
                choices=[
                    f"{endpoint.name} ({endpoint.num_indexes} indices)"
                    for endpoint in self.w.vector_search_endpoints.list_endpoints()
                ],
                label="Vector Search Endpoint",
                interactive=True,
                value=config.VECTOR_SEARCH_ENDPOINT_NAME,
            )

            tabel_name_box = gr.Textbox(
                label="Intent Table",
                interactive=True,
                value=config.CODE_INTENT_TABLE_NAME,
            )
            volume_name_box = gr.Textbox(
                label="Volume", interactive=True, value=config.VOLUME_NAME
            )
            vector_search_index_box = gr.Textbox(
                label="Vector Search Index",
                interactive=True,
                value=config.VS_INDEX_NAME,
            )

    def get_warehouse_name_by_id(self, warehouse_id):
        try:
            return self.w.warehouses.get(warehouse_id).name
        except Exception as e:
            return "Please select a valid warehouse"
