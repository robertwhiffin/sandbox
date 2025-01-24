import gradio as gr

from sql_migration_assistant.config import get_config
from sql_migration_assistant.frontend.components import get_foundation_model_dropdown

config = get_config()


class ConfigTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self, title: str, initialized: gr.Radio, visible=True):
        self.w = config.w
        with gr.Tab(label=title, visible=visible) as self.tab:
            self.header = gr.Markdown(f"## {title}")
            # self.embedding_model_endpoint_dropdown = gr.Dropdown(
            #     choices=[
            #         e.name
            #         for e in self.w.serving_endpoints.list()
            #         if e.task and "embedding" in e.task
            #     ],
            #     label="Embedding Endpoint",
            #     interactive=True,
            #     value=config.get("EMBEDDING_MODEL_ENDPOINT"),
            # )

            # self.vector_search_dropdown = gr.Dropdown(
            #     choices=[
            #         f"{endpoint.name} ({endpoint.num_indexes} indices)"
            #         for endpoint in self.w.vector_search_endpoints.list_endpoints()
            #     ],
            #     label="Vector Search Endpoint",
            #     interactive=True,
            #     value=config.get("VECTOR_SEARCH_ENDPOINT_NAME"),
            # )
            self.volume_dropdown = gr.Dropdown(
                choices=[
                    volume.name
                    for volume in self.w.volumes.list(
                        config.get("CATALOG"), config.get("SCHEMA")
                    )
                ],
                label="Volume",
                interactive=True,
                value=config.get("VOLUME"),
            )
            self.default_llm_dropdown = get_foundation_model_dropdown(
                self.tab, label="Default Foundation Endpoint"
            )

            self.intent_tabel_name_box = gr.Textbox(
                label="Intent Table",
                interactive=True,
                value=config.get("CODE_INTENT_TABLE_NAME"),
            )
            self.prompt_tabel_name_box = gr.Textbox(
                label="Intent Table",
                interactive=True,
                value=config.get("INSTRUCTIONS_TABLE_NAME"),
            )

            self.vector_search_index_box = gr.Textbox(
                label="Vector Search Index",
                interactive=True,
                value=config.get("VS_INDEX_NAME"),
            )

            self.save_config = gr.Button(
                f"Save {title}",
            )

            def set_configs(a, b, c, d, x, y, z):
                config.set_configs(
                    {
                        "EMBEDDING_MODEL_ENDPOINT": a,
                        "VECTOR_SEARCH_ENDPOINT_NAME": b,
                        "VOLUME": c,
                        "DEFAULT_LLM": d,
                        "CODE_INTENT_TABLE_NAME": x,
                        "INSTRUCTIONS_TABLE_NAME": y,
                        "VS_INDEX_NAME": z,
                    }
                )
                gr.Info("Configurations saved")
                if a and b and c and d:
                    return gr.update(value=True)
                return gr.update()

            self.save_config.click(
                set_configs,
                inputs=[
                   # self.embedding_model_endpoint_dropdown,
                   # self.vector_search_dropdown,
                    self.volume_dropdown,
                    self.default_llm_dropdown,
                    self.intent_tabel_name_box,
                    self.prompt_tabel_name_box,
                    self.vector_search_index_box,
                ],
                outputs=initialized,
            )
            self.tab.select(
                lambda: [
                    gr.update(
                        value=config.get("EMBEDDING_MODEL_ENDPOINT"),
                        choices=[
                            e.name
                            for e in self.w.serving_endpoints.list()
                            if e.task and "embedding" in e.task
                        ],
                    ),
                    gr.update(
                        value=config.get("VECTOR_SEARCH_ENDPOINT_NAME"),
                        choices=[
                            f"{endpoint.name} ({endpoint.num_indexes} indices)"
                            for endpoint in self.w.vector_search_endpoints.list_endpoints()
                        ],
                    ),
                    gr.update(
                        value=config.get("VOLUME"),
                        choices=[
                            volume.name
                            for volume in self.w.volumes.list(
                                config.get("CATALOG"), config.get("SCHEMA")
                            )
                        ],
                    ),
                    gr.update(value=config.get("CODE_INTENT_TABLE_NAME")),
                    gr.update(value=config.get("INSTRUCTIONS_TABLE_NAME")),
                    gr.update(value=config.get("VS_INDEX_NAME")),
                ],
                outputs=[
                   # self.embedding_model_endpoint_dropdown,
                   # self.vector_search_dropdown,
                    self.volume_dropdown,
                    self.intent_tabel_name_box,
                    self.prompt_tabel_name_box,
                    self.vector_search_index_box,
                ],
            )
