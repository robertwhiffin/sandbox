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

            self.default_llm_dropdown = get_foundation_model_dropdown(
                self.tab, label="Default Foundation Endpoint"
            )

            self.save_config = gr.Button(
                f"Save {title}",
            )

            def set_configs(

                    d,
            ):
                config.set_configs(
                    {
                        "DEFAULT_LLM": d,
                    }
                )
                gr.Info("Configurations saved")
                return gr.update(value=True)

            self.save_config.click(
                set_configs,
                inputs=[
                    self.default_llm_dropdown,
                ],
                outputs=initialized,
            )