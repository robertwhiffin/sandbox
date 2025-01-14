import gradio as gr
from databricks.sdk import WorkspaceClient
from tomlkit import value

from sql_migration_assistant.config import get_config
from sql_migration_assistant.utils import get_workspace_client, logger

config = get_config()
class ConfigTab:
    header: gr.Markdown
    tab: gr.Tab


    def __init__(self, title: str, visible=True):
        self.w = config.w
        with gr.Tab(label=title, visible=visible) as self.tab:
            self.header = gr.Markdown(f"## {title}")
            self.embedding_model_endpoint_dropdown = gr.Dropdown(
                choices=[
                    e.name
                    for e in self.w.serving_endpoints.list()
                    if e.task and "embedding" in e.task
                ],
                label="Embedding Endpoint",
                interactive=True,
                value=config.get("EMBEDDING_MODEL_ENDPOINT")
            )

            self.vector_search_dropdown = gr.Dropdown(
                choices=[
                    f"{endpoint.name} ({endpoint.num_indexes} indices)"
                    for endpoint in self.w.vector_search_endpoints.list_endpoints()
                ],
                label="Vector Search Endpoint",
                interactive=True,
                value=config.get("VECTOR_SEARCH_ENDPOINT_NAME")
            )
            self.volume_dropdown = gr.Dropdown(
                choices=[
                    volume.name
                    for volume in self.w.volumes.list(config.get("CATALOG"), config.get("SCHEMA"))
                ],
                label="Volume",
                interactive=True,
                value=config.get("VOLUME")
            )
            self.intent_tabel_name_box = gr.Textbox(
                label="Intent Table",
                interactive=True,
                value=config.get("CODE_INTENT_TABLE_NAME"),
            )
            self.prompt_tabel_name_box = gr.Textbox(
                label="Intent Table",
                interactive=True,
                value=config.get("PROMPT_TABLE"),
            )

            self.vector_search_index_box = gr.Textbox(
                label="Vector Search Index",
                interactive=True,
                value=config.get("VS_INDEX_NAME"),
            )

            self.embedding_model_endpoint_dropdown.select(lambda x: config.set_config("EMBEDDING_MODEL_ENDPOINT",x), inputs=self.embedding_model_endpoint_dropdown)
            self.vector_search_dropdown.select(lambda x: config.set_config("VECTOR_SEARCH_ENDPOINT_NAME",x),
                                                          inputs=self.vector_search_dropdown)
            self.volume_dropdown.select(lambda x: config.set_config("VOLUME",x),
                                                          inputs=self.volume_dropdown)
            self.save_config = gr.Button(f"Save {title}")
            def set_names(x, y, z):
                config.set_config("CODE_INTENT_TABLE_NAME", x)
                config.set_config("PROMPT_TABLE", y)
                config.set_config("VS_INDEX_NAME", z)

            self.save_config.click(set_names,
                                   inputs=[self.intent_tabel_name_box,self.prompt_tabel_name_box,self.vector_search_index_box]
                                   )
            self.tab.select(lambda : [gr.update(value=config.get("EMBEDDING_MODEL_ENDPOINT")),
                                      gr.update(value=config.get("VECTOR_SEARCH_ENDPOINT_NAME")),
                                      gr.update(value=config.get("VOLUME")),
                                      gr.update(value=config.get("CODE_INTENT_TABLE_NAME")),
                                      gr.update(value=config.get("PROMPT_TABLE")),
                                      gr.update(value=config.get("VS_INDEX_NAME"))],
                            outputs=[self.embedding_model_endpoint_dropdown,
                                     self.vector_search_dropdown,
                                     self.volume_dropdown,
                                     self.intent_tabel_name_box,
                                     self.prompt_tabel_name_box,
                                     self.vector_search_index_box])
