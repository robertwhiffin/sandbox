import gradio as gr

from sql_migration_assistant.config import get_config

config = get_config()

pay_per_token_models = [
    "databricks-meta-llama-3-1-405b-instruct",
    "databricks-meta-llama-3-1-70b-instruct",
    "databricks-dbrx-instruct",
    "databricks-mixtral-8x7b-instruct",
]


def get_foundation_model_dropdown(tab):
    foundation_model_dropdown = gr.Dropdown(
        choices=[
            ("" if e.name not in pay_per_token_models else "PPT - ") + e.name
            for e in config.w.serving_endpoints.list()
            if e.name
        ],
        interactive=True,
        label="Language Model",
    )
    tab.select(lambda:
                    gr.update(choices=[
            ("" if e.name not in pay_per_token_models else "PPT - ") + e.name
            for e in config.w.serving_endpoints.list()
            if e.name
        ]), outputs=foundation_model_dropdown)
    return foundation_model_dropdown
