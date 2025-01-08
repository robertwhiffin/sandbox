import gradio as gr


class InstructionsTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Instructions") as self.tab:
            self.header = gr.Markdown(
                """
        Legion is an AI powered tool that aims to accelerate the migration of code to Databricks for low cost and effort. It 
        does this by using AI to translate, explain, and make discoverable your code. 
        
        This interface is the Legion Control Panel. Here you are able to configure the AI agents for translation and explanation
        to fit your needs, incorporating your expertise and knowledge of the codebase by adjusting the AI agents' instructions.
        
        ## Operational Parameters:
        
        ### *Interactive mode*
        Fine tune the AI agents on a single file and output the result as a Databricks notebook. 
        Use this UI to adjust the system prompts and instructions for the AI agents to generate the best translation and intent.
        
        ### *Batch mode*
        Process a Volume of files to generate Databricks notebooks. Use this UI to fine tune your agent prompts against selected
        files before executing a Workflow to transform all files in the Volume, outputting Databricks notebooks with the AI
        generated intent and translation.
        
        ### *Code syntax highlighting*
        
        Select your input and output code languages below to apply syntax highlighting. This is purely for visual 
        purposes and has no effect on how the tool operates.
        
        
        Please select your  mode of operation to get started.   
        
        """
            )
            with gr.Row():
                self.operation = gr.Radio(
                    label="Select operation mode",
                    choices=["Interactive mode", "Batch mode"],
                    value="Interactive mode",
                    type="value",
                    interactive=True,
                )
                self.input_language = gr.Dropdown(
                    label="Select input code language syntax",
                    # the r formatter doesn't do anything, and switching to None doesn't seem to update the code boxes
                    # away from their previous value. So will only offer choices of SQL, Python, or no formatting.
                    choices=[
                        ("SQL", "sql"),
                        ("Python", "python"),
                        ("No formatting", "r"),
                    ],
                    value="sql",
                    type="value",
                    interactive=True,
                )
                self.output_language = gr.Dropdown(
                    label="Select output code language syntax",
                    # the r formatter doesn't do anything, and switching to None doesn't seem to update the code boxes
                    # away from their previous value. So will only offer choices of SQL, Python, or no formatting.
                    choices=[
                        ("SQL", "sql"),
                        ("Python", "python"),
                        ("No formatting", "r"),
                    ],
                    value="sql",
                    type="value",
                    interactive=True,
                )
