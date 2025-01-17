import gradio as gr

from sql_migration_assistant.config import get_config

config = get_config()

def get_foundation_endpoints():
    return [
            ("" if not e.name.startswith("databricks") else "PPT - ") + e.name
            for e in config.w.serving_endpoints.list()
            if e.task and e.task.endswith("chat")
        ]

def get_foundation_model_dropdown(model_name, tab):
    foundation_model_dropdown = gr.Dropdown(
        choices=get_foundation_endpoints(),
        label="Foundation Endpoint",
        interactive=True,
        value=config.get(model_name),
    )
    foundation_model_dropdown.change(
        lambda x: config.set_config(
            model_name, x if not x.startswith("PPT - ") else x[6:]
        ),
        inputs=foundation_model_dropdown,
    )
    tab.select(lambda:
                    gr.update(choices=get_foundation_endpoints()), outputs=foundation_model_dropdown)
    return foundation_model_dropdown
