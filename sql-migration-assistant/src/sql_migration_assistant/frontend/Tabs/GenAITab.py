from dataclasses import dataclass
from enum import Enum

import gradio as gr

from sql_migration_assistant.config import get_config
from sql_migration_assistant.frontend.callbacks import (
    llm_wrapper,
    get_prompt_details,
    prompt_helper,
)
from sql_migration_assistant.frontend.components import get_foundation_model_dropdown

config = get_config()

class Purpose(Enum):
    EXPLAIN= "explain"
    TRANSLATE = "translate"

@dataclass
class Parameters:
    title: str
    header: str
    prompt_title: str
    prompt_label: str
    prompt_placeholder: str
    prompt_lines: int
    button_title: str
    result_header: str
    model_name: str

PARAMETERS = {
    Purpose.EXPLAIN: Parameters(
        title="Code Explanation",
        header= """
                ## An AI tool to generate the intent of your code.

                In this tab you define the instructions for the AI agent on explaining the code. 
                This intent will be stored in Unity Catalog, and can be used for finding similar code, for documentation, 
                 and to help with writing new code in Databricks to achieve the same goal.

                Once you are happy with your prompt, or you wish to explore and adapt the instructions others have used, 
                you can do so in the *Load / save instructions* section. 
                """,
        prompt_title=""" ## Explaining code with AI.""",
        prompt_label="AI instructions for explaining the code",
        prompt_placeholder="Add your instructions here, for example:\n"
                            "Explain the intent of this code. Provide a concise summary of the intent of this code.\n"
                            "This should be a description of the overall purpose of the code, not a breakdown of how the code achieves this purpose.\n"
                            "Next, provide high level bullet points of the main steps in the code. This should be a list of the main steps in the code"
                            ", not a line by line breakdown.\n",
        prompt_lines=4,
        button_title="Explain",
        result_header=""" ## Code Explanation.""",
        model_name="INTENT_MODEL_NAME"
    ),
Purpose.TRANSLATE: Parameters(
        title="Code Translation",
        header= """
                ## An AI tool to translate your code.
        
                In this tab you define the instructions for the AI agent on translating the code.
                
                Follow prompt engineering [best practices](https://www.databricks.com/glossary/prompt-engineering). Start 
                simple and add complexity. 
                
                
                Once you are happy with your prompt, or you wish to explore and adapt the instructions others have used, 
                you can do so in the *Load / save instructions* section. 
                """,
        prompt_title=""" ## AI Code Translation.""",
        prompt_label="Instructions for the LLM translation tool.",
        prompt_placeholder="Add your system prompt here, for example:\n"
                "Your job is to help move code from SQL-Server to Databricks. You are an expert in Spark, Delta Lake, "
                "and SQL Server. You return valid code - do not prefix your code with backticks or an "
                "English introduction.",
        prompt_lines=3,
        button_title="Translate",
        result_header=""" ## Translated Code""",
        model_name="TRANSLATION_MODEL_NAME"
    )
}


class GenAITab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self, purpose: Purpose, visible=True):
        params = PARAMETERS[purpose]
        with gr.Tab(label=params.title, visible=visible) as self.tab:
            self.header = gr.Markdown(
                params.header,
            )
            self.foundation_model_dropdown = get_foundation_model_dropdown(
                "INTENT_MODEL_NAME", self.tab
            )
            with gr.Accordion(label="Advanced Settings", open=False):
                gr.Markdown(
                    """ ### Advanced settings for model.

                    The *Temperature* parameter controls the randomness of the AI's response. Higher values will result in 
                    more creative responses, while lower values will result in more predictable responses.
                    """
                )

                with gr.Row():
                    self.temperature = gr.Number(
                        label="Temperature. Float between 0.0 and 1.0", value=0.0
                    )
                    self.max_tokens = gr.Number(
                        label="Max tokens. Check your LLM docs for limit.", value=3500
                    )

            with gr.Accordion(label="Load / save instructions", open=False):
                gr.Markdown(
                    """ ### Load a previously saved prompt.
                    """
                )
                # these bits relate to saving and loading of prompts
                with gr.Row():
                    self.save_instructions = gr.Button("Save Agent Configuration")
                    self.load_instructions = gr.Button("Retrieve Saved Configurations")
                # hidden button and display box for saved prompts, made visible when the load button is clicked
                self.loading_instructions = gr.Markdown(
                    "To load a saved configuration, enter the ID value in the *ID to load* box and click the *Load Agent Configuration Button*.",
                    visible=False,
                )
                with gr.Row():
                    self.prompt_id_to_load = gr.Textbox(
                        label="ID to load",
                        visible=False,
                        placeholder="Enter the ID of the configuration to load from the table below.",
                    )
                    self.load_agent_config = gr.Button(
                        "Load Agent Configuration",
                        visible=False,
                    )
                self.loaded_instructions = gr.Dataframe(
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

            # with gr.Accordion(label="Intent Pane", open=True):
            gr.Markdown(params.prompt_title)
            self.system_prompt = gr.Textbox(
                label=params.prompt_label,
                placeholder=params.prompt_placeholder,
                lines=params.prompt_lines,
            )
            self.explain_button = gr.Button(params.button_title)
            with gr.Row():
                with gr.Column():
                    gr.Markdown(""" ## Input Code.""")

                    # input code box
                    self.input_code = gr.Code(
                        label="Input Code",
                        language="sql",  # default, this can be updated
                    )

                with gr.Column():
                    # divider subheader
                    gr.Markdown(params.result_header)
                    # output box of the translated code
                    if purpose == Purpose.EXPLAIN:
                        self.output = gr.Markdown(
                            label="AI Agent Output.", elem_classes="custom-markdown"
                        )
                    elif purpose == Purpose.TRANSLATE:
                        self.output = gr.Code(
                            label="AI Agent output", language="sql-sparkSQL", lines=4
                        )

                # reset hidden chat history and prompt
                # do translation
                self.explain_button.click(
                    fn=llm_wrapper,
                    inputs=[
                        self.system_prompt,
                        self.input_code,
                        self.foundation_model_dropdown,
                        self.max_tokens,
                        self.temperature,
                    ],
                    outputs=self.output,
                )
                # get the prompts and populate the table and make it visible
                #self.load_prompt.click(
                #    fn=lambda: gr.update(
                #        visible=True,
                #        value=prompt_helper.get_prompts("intent_agent"),
                #    ),
                #   inputs=None,
                #    outputs=[self.loaded_intent_prompts],
                #)
                # make the input box for the prompt id visible
                self.load_instructions.click(
                    fn=lambda: [gr.update(visible=True)] * 3,
                    inputs=None,
                    outputs=[
                        self.prompt_id_to_load,
                        self.load_agent_config,
                        self.loading_instructions,
                    ],
                )

                self.load_agent_config.click(
                    fn=get_prompt_details,
                    inputs=[
                        self.prompt_id_to_load,
                        self.loaded_instructions,
                    ],
                    outputs=[
                        self.system_prompt,
                        self.temperature,
                        self.max_tokens,
                    ],
                )
                # save the prompt
                # self.save_prompt.click(
                #     fn=lambda prompt, temp, tokens: prompt_helper.save_prompt(
                #         "intent_agent", prompt, temp, tokens
                #     ),
                #     inputs=[
                #         self.intent_system_prompt,
                #         self.intent_temperature,
                #         self.intent_max_tokens,
                #     ],
                #     outputs=None,
                # )
