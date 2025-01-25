import gradio as gr

from sql_migration_assistant.config import get_config
from sql_migration_assistant.frontend.callbacks import list_files

config = get_config()


class BatchInputCodeTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self, visible=True):
        with gr.Tab(label="Select code", visible=visible) as self.tab:
            self.header = gr.Markdown(
                f"""## Select a file to test your agents on.   

               Legion can batch process a Volume of files to generate Databricks notebooks. The files to translate must be 
               added to the *Input Code* folder in the UC Volume [here]({config.w.config.host}/explore/data/volumes/{config.catalog}/{config.get('SCHEMA')}/{config.get('VOLUME')}). 

               Note - every file present will be processed in batch mode.
               
               Here you can select a file to fine tune your agent prompts against. 
                """
            )
            self.volume_path = gr.Textbox(
                value=config.get("VOLUME_NAME_INPUT_PATH"),
                visible=False
            )


            self.load_files = gr.Button("Load Files from Volume")
            self.select_code_file = gr.Radio(label="Select Code File")
            self.selected_file = gr.Code(label="Selected Code File", language="sql")

            self.load_files.click(list_files, self.volume_path, self.select_code_file)
