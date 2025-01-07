import gradio as gr

from sql_migration_assistant.frontend.callbacks import (
    llm_translate_wrapper,
    prompt_helper,
    get_prompt_details,
)


class TranslationTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Translation") as tab:
            self.tab = tab
            self.header = gr.Markdown(
                """
            ## An AI tool to translate your code.
    
            In this tab you define the instructions for the AI agent on translating the code.
            
            Follow prompt engineering [best practices](https://www.databricks.com/glossary/prompt-engineering). Start 
            simple and add complexity. 
            """
            )
            with gr.Accordion(label="Advanced Settings", open=False):
                gr.Markdown(
                    """ ### Advanced settings for the translation AI Agent.

                    The *Temperature* parameter controls the randomness of the AI's response. Higher values will result in 
                    more creative responses, while lower values will result in more predictable responses.
                    """
                )
                with gr.Row():
                    self.translation_temperature = gr.Number(
                        label="Temperature. Float between 0.0 and 1.0", value=0.0
                    )
                    self.translation_max_tokens = gr.Number(
                        label="Max tokens. Check your LLM docs for limit.", value=12500
                    )
            with gr.Accordion(label="Load / save instructions", open=False):
                gr.Markdown(
                    """ ### Load a previously saved prompt.
                    """
                )
                with gr.Row():
                    self.save_translation_prompt = gr.Button("Save translation prompt")
                    self.load_translation_prompt = gr.Button("Load translation prompt")
                # hidden button and display box for saved prompts, made visible when the load button is clicked
                self.translation_prompt_id_to_load = gr.Textbox(
                    label="Prompt ID to load",
                    visible=False,
                    placeholder="Enter the ID of the prompt to load from the table below.",
                )
                self.loaded_translation_prompts = gr.Dataframe(
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


            #with gr.Accordion(label="Translation Pane", open=True):
            gr.Markdown(""" ## AI Code Translation.""")
            # a button labelled translate
            self.translation_system_prompt = gr.Textbox(
                label="Instructions for the LLM translation tool.",
                placeholder="Add your system prompt here, for example:\n"
                "Your job is to help move code from SQL-Server to Databricks. You are an expert in Spark, Delta Lake, "
                            "and SQL Server. You return valid code - do not prefix your code with backticks or an "
                            "English introduction.",
                lines=3,
            )
            self.translate_button = gr.Button("Translate")
            with gr.Row():
                with gr.Column():
                    gr.Markdown(""" ## Input code.""")

                    # input box for SQL code with nice formatting
                    self.translation_input_code = gr.Code(
                        label="Input Code",
                        language="sql",
                    )

                with gr.Column():
                    # divider subheader
                    gr.Markdown(""" ## Translated Code""")
                    # output box of the T-SQL translated to Spark SQL
                    self.translated = gr.Code(
                        label="AI Agent output",
                        language="sql-sparkSQL",
                        lines=4
                    )

                # reset hidden chat history and prompt
                # do translation
                self.translate_button.click(
                    fn=llm_translate_wrapper,
                    inputs=[
                        self.translation_system_prompt,
                        self.translation_input_code,
                        self.translation_max_tokens,
                        self.translation_temperature,
                    ],
                    outputs=self.translated,
                )
                # get the prompts and populate the table and make it visible
                self.load_translation_prompt.click(
                    fn=lambda: gr.update(
                        visible=True,
                        value=prompt_helper.get_prompts("translation_agent"),
                    ),
                    inputs=None,
                    outputs=[self.loaded_translation_prompts],
                )
                # make the input box for the prompt id visible
                self.load_translation_prompt.click(
                    fn=lambda: gr.update(visible=True),
                    inputs=None,
                    outputs=[self.translation_prompt_id_to_load],
                )
                # retrive the row from the table and populate the system prompt, temperature, and max tokens
                self.translation_prompt_id_to_load.change(
                    fn=get_prompt_details,
                    inputs=[
                        self.translation_prompt_id_to_load,
                        self.loaded_translation_prompts,
                    ],
                    outputs=[
                        self.translation_system_prompt,
                        self.translation_temperature,
                        self.translation_max_tokens,
                    ],
                )
                self.save_translation_prompt.click(
                    fn=lambda prompt, temp, tokens: prompt_helper.save_prompt(
                        "translation_agent", prompt, temp, tokens
                    ),
                    inputs=[
                        self.translation_system_prompt,
                        self.translation_temperature,
                        self.translation_max_tokens,
                    ],
                    outputs=None,
                )