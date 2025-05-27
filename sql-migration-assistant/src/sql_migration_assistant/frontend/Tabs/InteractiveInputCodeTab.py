import gradio as gr


class InteractiveInputCodeTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self, visible=True):
        with gr.Tab(label="Input code", visible=visible) as self.tab:
            self.header = gr.Markdown(
                f"""## Paste your code below and click the "Ingest code".   
                """
            )
            self.interactive_code_button = gr.Button("Ingest code")
            self.interactive_code = gr.Code(
                label="Paste your code in here", language="sql"
            )
            self.interactive_code_button.click(fn=lambda: gr.Info("Code ingested!"))
