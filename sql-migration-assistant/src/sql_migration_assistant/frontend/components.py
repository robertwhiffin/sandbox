import gradio as gr

from sql_migration_assistant.config import get_config

config = get_config()

pay_per_token_models = [
        "databricks-meta-llama-3-1-405b-instruct",
        "databricks-meta-llama-3-1-70b-instruct",
        "databricks-dbrx-instruct",
        "databricks-mixtral-8x7b-instruct",
    ]

def get_foundation_model_dropdown(model_name):
    foundation_model_dropdown = gr.Dropdown(
        choices=[
            ("" if e.name not in pay_per_token_models else "PPT - ")
            + e.name
            for e in config.w.serving_endpoints.list()
            if e.name
        ],
        label="Foundation Endpoint",
        interactive=True,
        value=config.get(model_name),
    )
    foundation_model_dropdown.change(
        lambda x: config.set_config(model_name, x if not x.startswith("PPT - ") else x[6:]),
        inputs=foundation_model_dropdown)
    return foundation_model_dropdown
