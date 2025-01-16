from dataclasses import dataclass
from enum import Enum

import gradio as gr

from sql_migration_assistant.config import get_config
from sql_migration_assistant.frontend.callbacks import (
    llm_wrapper,
    save_instruction,
    load_instructions,
)
from sql_migration_assistant.frontend.components import get_foundation_model_dropdown

config = get_config()


class Purpose(Enum):
    EXPLAIN = "explain"
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


PARAMETERS = {
    Purpose.EXPLAIN: Parameters(
        title="Code Explanation",
        header="""
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
    ),
    Purpose.TRANSLATE: Parameters(
        title="Code Translation",
        header="""
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
    ),
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
            with gr.Column(elem_classes="custom-container"):

                gr.Markdown(
                    """
                ## Agent Configuration
                You can configure the AI here. These consist of a LLM you want to use and instructions you give to this LLM.
                You can also save/load instructions.
                """
                )
                self.foundation_model_dropdown = get_foundation_model_dropdown(self.tab)
                gr.Markdown(
                    """ ### Advanced settings for model.

                    The *Temperature* parameter controls the randomness of the AI's response. Higher values will result in 
                    more creative responses, while lower values will result in more predictable responses.
                    """
                )
                with gr.Accordion(label="Advanced settings for model.", open=False):
                    with gr.Row():
                        self.temperature = gr.Number(
                            label="Temperature. Float between 0.0 and 1.0", value=0.0
                        )
                        self.max_tokens = gr.Number(
                            label="Max tokens. Check your LLM docs for limit.",
                            value=3500,
                        )

                self.system_prompt = gr.Textbox(
                    label=params.prompt_label,
                    placeholder=params.prompt_placeholder,
                    lines=params.prompt_lines,
                )
                with gr.Accordion(
                    label="Save and load Agent Configuration", open=False
                ):
                    with gr.Row():
                        self.instruction_name = gr.Textbox(
                            max_lines=1,
                            placeholder="Please fill in a name to save your instructions",
                            label="Configuration Name",
                        )
                        self.save_instructions = gr.Button("Save Agent Configuration")
                    with gr.Row():
                        self.instructions_dropdown = gr.Dropdown(
                            label="Existing Agent Configurations",
                            choices=load_instructions(purpose.value)["name"].to_list(),
                            value=None,
                        )
                        self.load_instructions = gr.Button("Load Agent Configurations")

            # with gr.Accordion(label="Intent Pane", open=True):
            gr.Markdown(params.prompt_title)

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

        def save_instructions_wrapper(*args):
            save_instruction(*args, instruction_type=purpose.value)
            return gr.update(choices=load_instructions(purpose.value)["name"].to_list())

        self.save_instructions.click(
            save_instructions_wrapper,
            inputs=[
                self.instruction_name,
                self.foundation_model_dropdown,
                self.temperature,
                self.max_tokens,
                self.system_prompt,
            ],
            outputs=self.instructions_dropdown,
        )

        def load_single_instruction(name: str):
            instruction = load_instructions(purpose.value, name).iloc[0]
            return [
                gr.update(value=instruction["name"]),
                gr.update(value=instruction["endpoint"]),
                gr.update(value=int(instruction["max_tokens"])),
                gr.update(value=float(instruction["temperature"])),
                gr.update(value=instruction["system_prompt"]),
            ]

        self.load_instructions.click(
            load_single_instruction,
            inputs=[self.instructions_dropdown],
            outputs=[
                self.instruction_name,
                self.foundation_model_dropdown,
                self.max_tokens,
                self.temperature,
                self.system_prompt,
            ],
        )
