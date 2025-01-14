import gradio as gr

from sql_migration_assistant.config import DATABRICKS_HOST, CATALOG, SCHEMA, VOLUME_NAME
from sql_migration_assistant.frontend.callbacks import write_adhoc_to_workspace


class InteractiveOutputTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self, visible=True):
        with gr.Tab(label="Write file to Workspace", visible=visible) as self.tab:
            self.header = gr.Markdown(
                f""" ## Write to Workspace

            Write out your explained and translated file to a notebook in the workspace. 
            You must provide a filename for the notebook. The notebook will be written to the workspace, saved to the 
            Output Code location in the Unity Catalog Volume [here]({DATABRICKS_HOST}/explore/data/volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}) 
            , and the intent will be saved to the intent table. 
            """
            )
            template = """
        -- Databricks notebook source
        -- MAGIC %md
        -- MAGIC # This notebook was AI generated. AI can make mistakes. This is provided as a tool to accelerate your migration. 
        -- MAGIC
        -- MAGIC ### AI Generated Intent
        -- MAGIC
        -- MAGIC INTENT_GOES_HERE
        
        -- COMMAND ----------
        
        TRANSLATED_CODE_GOES_HERE
              """
            # this is ahidden box which will hold the url of the output notebook, which can be passed to the save intent
            # function
            self.hidden_url_textbox = gr.Textbox(
                visible=False
            )
            with gr.Row():
                self.produce_preview_button = gr.Button("Produce Preview")
                with gr.Column():
                    self.file_name = gr.Textbox(label="Filename for the notebook")
                    self.write_to_workspace_button = gr.Button("Write to Workspace")
                    self.adhoc_write_output = gr.Markdown(
                        label="Notebook output location"
                    )

            self.preview = gr.Code(label="Preview", language="python")


