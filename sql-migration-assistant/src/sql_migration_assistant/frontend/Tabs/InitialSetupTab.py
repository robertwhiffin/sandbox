import gradio as gr
from databricks.sdk import WorkspaceClient
from tomlkit import value

from sql_migration_assistant.config import config
from sql_migration_assistant.utils import get_workspace_client, logger


class InitialSetupTab:
    header: gr.Markdown
    tab: gr.Tab


    def __init__(self, visible=True):
        self.w = get_workspace_client(config.get("DATABRICKS_PROFILE"))
        with gr.Tab(label="Initial Setup", visible=visible) as self.tab:
            self.header = gr.Markdown("## Initial Setup")
            self.embedding_model_endpoint_dropdown = gr.Dropdown(
                choices=[
                    e.name
                    for e in self.w.serving_endpoints.list()
                    if e.task and "embedding" in e.task
                ],
                label="Embedding Endpoint",
                interactive=True,
                value=None
            )

            self.vector_search_dropdown = gr.Dropdown(
                choices=[
                    f"{endpoint.name} ({endpoint.num_indexes} indices)"
                    for endpoint in self.w.vector_search_endpoints.list_endpoints()
                ],
                label="Vector Search Endpoint",
                interactive=True,
                value=None
            )
            self.volume_dropdown = gr.Dropdown(
                choices=[
                    volume.name
                    for volume in self.w.volumes.list(config.get("CATALOG"), config.get("SCHEMA"))
                ],
                label="Volume",
                interactive=True,
                value=None
            )

            self.embedding_model_endpoint_dropdown.select(lambda x: config.set_config("EMBEDDING_MODEL_ENDPOINT",x), inputs=self.embedding_model_endpoint_dropdown)
            self.vector_search_dropdown.select(lambda x: config.set_config("VECTOR_SEARCH_ENDPOINT",x),
                                                          inputs=self.vector_search_dropdown)
            self.volume_dropdown.select(lambda x: config.set_config("VOLUME",x),
                                                          inputs=self.volume_dropdown)
            self.save_config = gr.Button("Save Initial Configuration")
