import gradio as gr
from databricks.sdk import WorkspaceClient

from sql_migration_assistant.config import get_config
from sql_migration_assistant.frontend.callbacks import (
    llm_intent_wrapper,
    get_prompt_details,
    prompt_helper,
)
from sql_migration_assistant.frontend.components import get_foundation_model_dropdown

config = get_config()

class CodeExplanationTab:
    header: gr.Markdown
    tab: gr.Tab



    def __init__(self, visible=True):
        with gr.Tab(label="Code Explanation", visible=visible) as self.tab:
            self.header = gr.Markdown(
                """
                ## An AI tool to generate the intent of your code.
        
                In this tab you define the instructions for the AI agent on explaining the code. 
                This intent will be stored in Unity Catalog, and can be used for finding similar code, for documentation, 
                 and to help with writing new code in Databricks to achieve the same goal.
                 
                Once you are happy with your prompt, or you wish to explore and adapt the instructions others have used, 
                you can do so in the *Load / save instructions* section. 
                """
            )
            self.foundation_model_dropdown = get_foundation_model_dropdown("INTENT_MODEL_NAME")
            with gr.Accordion(label="Advanced Settings", open=False):
                gr.Markdown(
                    """ ### Advanced settings for the generating the intent of the input code.

                    The *Temperature* parameter controls the randomness of the AI's response. Higher values will result in 
                    more creative responses, while lower values will result in more predictable responses.
                    """
                )

                with gr.Row():
                    self.intent_temperature = gr.Number(
                        label="Temperature. Float between 0.0 and 1.0", value=0.0
                    )
                    self.intent_max_tokens = gr.Number(
                        label="Max tokens. Check your LLM docs for limit.", value=3500
                    )

            with gr.Accordion(label="Load / save instructions", open=False):
                gr.Markdown(
                    """ ### Load a previously saved prompt.
                    """
                )
                    # these bits relate to saving and loading of prompts
                with gr.Row():
                    self.save_intent_prompt = gr.Button("Save Agent Configuration")
                    self.load_intent_prompt = gr.Button("Retrieve Saved Configurations")
                # hidden button and display box for saved prompts, made visible when the load button is clicked
                self.loading_instructions = gr.Markdown(
                    "To load a saved configuration, enter the ID value in the *ID to load* box and click the *Load Agent Configuration Button*."
                    ,visible=False
                )
                with gr.Row():
                    self.intent_prompt_id_to_load = gr.Textbox(
                        label="ID to load",
                        visible=False,
                        placeholder="Enter the ID of the configuration to load from the table below.",
                    )
                    self.load_intent_agent_config = gr.Button(
                        "Load Agent Configuration",
                        visible=False,
                    )
                self.loaded_intent_prompts = gr.Dataframe(
                    label="Saved prompts.",
                    visible=False,
                    headers=[
                        "id",
                        "Prompt",
                        "Temperature",
                        "Max Tokens",
                        "Save Datetime",
                    ],
                    interactive=False,
                    wrap=True,
                )


            #with gr.Accordion(label="Intent Pane", open=True):
            gr.Markdown(
                """ ## Explaining code with AI."""
            )
            self.intent_system_prompt = gr.Textbox(
                label="AI instructions for explaining the code",
                placeholder="Add your instructions here, for example:\n"
                            "Explain the intent of this code. Provide a concise summary of the intent of this code.\n"
                            "This should be a description of the overall purpose of the code, not a breakdown of how the code achieves this purpose.\n"
                            "Next, provide high level bullet points of the main steps in the code. This should be a list of the main steps in the code"
                            ", not a line by line breakdown.\n",
                lines=4,
            )
            self.explain_button = gr.Button("Explain")
            with gr.Row():
                with gr.Column():
                    gr.Markdown(""" ## Input Code.""")

                    # input code box
                    self.intent_input_code = gr.Code(
                        label="Input Code",
                        language="sql", # default, this can be updated
                    )

                with gr.Column():
                    # divider subheader
                    gr.Markdown(""" ## Code Explanation.""")
                    # output box of the translated code
                    self.explained = gr.Textbox(
                        label="AI Agent Output.",
                        interactive=False,
                        lines=4
                    )

                # reset hidden chat history and prompt
                # do translation
                self.explain_button.click(
                    fn=llm_intent_wrapper,
                    inputs=[
                        self.intent_system_prompt,
                        self.intent_input_code,
                        self.foundation_model_dropdown,
                        self.intent_max_tokens,
                        self.intent_temperature,
                    ],
                    outputs=self.explained,
                )
                # get the prompts and populate the table and make it visible
                self.load_intent_prompt.click(
                    fn=lambda: gr.update(
                        visible=True,
                        value=prompt_helper.get_prompts("intent_agent"),
                    ),
                    inputs=None,
                    outputs=[self.loaded_intent_prompts],
                )
                # make the input box for the prompt id visible
                self.load_intent_prompt.click(
                    fn=lambda: [gr.update(visible=True)]*3,
                    inputs=None,
                    outputs=[self.intent_prompt_id_to_load, self.load_intent_agent_config, self.loading_instructions],
                )

                self.load_intent_agent_config.click(
                    fn=get_prompt_details,
                    inputs=[
                        self.intent_prompt_id_to_load,
                        self.loaded_intent_prompts,
                    ],
                    outputs=[
                        self.intent_system_prompt,
                        self.intent_temperature,
                        self.intent_max_tokens,
                    ],
                )
                # save the prompt
                self.save_intent_prompt.click(
                    fn=lambda prompt, temp, tokens: prompt_helper.save_prompt(
                        "intent_agent", prompt, temp, tokens
                    ),
                    inputs=[
                        self.intent_system_prompt,
                        self.intent_temperature,
                        self.intent_max_tokens,
                    ],
                    outputs=None,
                )
