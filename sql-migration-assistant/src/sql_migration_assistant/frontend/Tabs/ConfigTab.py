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

            self.volume_folder_dropdown = gr.Dropdown(
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

            self.prompt_tabel_name_box = gr.Textbox(
                label="Instructions Table",
                interactive=True,
                value=config.get("INSTRUCTIONS_TABLE_NAME"),
            )

            self.save_config = gr.Button(
                f"Save {title}",
            )

            def set_configs(
                    c,
                    d,
                    y,
            ):
                config.set_configs(
                    {
                        "VOLUME": c,
                        "DEFAULT_LLM": d,
                        "INSTRUCTIONS_TABLE_NAME": y,
                    }
                )
                gr.Info("Configurations saved")
                if c and d:
                    return gr.update(value=True)
                return gr.update(value=True)

            self.save_config.click(
                set_configs,
                inputs=[
                    self.volume_folder_dropdown,
                    self.default_llm_dropdown,
                    self.prompt_tabel_name_box,
                ],
                outputs=initialized,
            )
            self.tab.select(
                lambda: [
                    gr.update(
                        value=config.get("VOLUME"),
                        choices=[
                            volume.name
                            for volume in self.w.volumes.list(
                                config.get("CATALOG"), config.get("SCHEMA")
                            )
                        ],
                    ),
                    gr.update(value=config.get("INSTRUCTIONS_TABLE_NAME")),
                ],
                outputs=[
                    self.volume_folder_dropdown,
                    self.prompt_tabel_name_box,
                ],
            )
