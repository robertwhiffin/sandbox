import gradio as gr
from pyarrow import output_stream

from sql_migration_assistant.config import get_config
from sql_migration_assistant.frontend.Tabs.BatchInputCodeTab import BatchInputCodeTab
from sql_migration_assistant.frontend.Tabs.BatchOutputTab import BatchOutputTab
from sql_migration_assistant.frontend.Tabs.CodeExplanationTab import CodeExplanationTab
from sql_migration_assistant.frontend.Tabs.ConfigTab import ConfigTab
from sql_migration_assistant.frontend.Tabs.InstructionsTab import InstructionsTab
from sql_migration_assistant.frontend.Tabs.InteractiveInputCodeTab import (
    InteractiveInputCodeTab,
)
from sql_migration_assistant.frontend.Tabs.InteractiveOutputTab import (
    InteractiveOutputTab,
)
from sql_migration_assistant.frontend.Tabs.SimilarCodeTab import SimilarCodeTab
from sql_migration_assistant.frontend.Tabs.TranslationTab import TranslationTab
from sql_migration_assistant.frontend.callbacks import (
    read_code_file,
    produce_preview,
    execute_workflow,
    write_adhoc_to_workspace,
)
from sql_migration_assistant.utils import logger

config = get_config()


class GradioFrontend:
    intro = """<img align="right" src="https://asset.brandfetch.io/idSUrLOWbH/idm22kWNaH.png" alt="logo" width="120">

# Databricks Legion Migration Accelerator
"""

    def __init__(self):
        with gr.Blocks(theme=gr.themes.Soft()) as self.app:
            self.intro_markdown = gr.Markdown(self.intro)
            with gr.Tabs() as self.tabs:
                self.initialized = config.initial_setup_done()

                self.initial_setup = ConfigTab("Initial Setup", not self.initialized)
                self.instructions_tab = InstructionsTab(False)

                self.interactive_input_code_tab = InteractiveInputCodeTab(False)
                self.batch_input_code_tab = BatchInputCodeTab(False)
                self.code_explanation_tab = CodeExplanationTab(False)
                self.translation_tab = TranslationTab(False)
                self.similar_code_tab = SimilarCodeTab(False)
                self.batch_output_tab = BatchOutputTab(False)
                self.interactive_output_tab = InteractiveOutputTab(False)
                self.config_tab = ConfigTab("Configuration", False)

            def set_initialized(initial: bool=True):
                if config.initial_setup_done() and initial:
                    self.initialized = True
                    return [
                        gr.update(visible=False),
                        gr.update(visible=True),
                        gr.Tabs(selected=self.instructions_tab.tab.id),
                    ]
                return [gr.update(), gr.update(), gr.update()]

            def save_config(initial):
                def inner(a, b, c, x, y, z):
                    config.set_configs({"EMBEDDING_MODEL_ENDPOINT": a,
                                        "VECTOR_SEARCH_ENDPOINT_NAME": b,
                                        "VOLUME": c,
                                        "CODE_INTENT_TABLE_NAME": x,
                                        "PROMPT_TABLE": y,
                                        "VS_INDEX_NAME": z
                                        })
                    return set_initialized(initial)
                return inner

            self.app.load(
                set_initialized,
                inputs=None,
                outputs=[self.initial_setup.tab, self.instructions_tab.tab, self.tabs],
            )
            self.initial_setup.save_config.click(
                save_config(True),
                show_progress="full",
                inputs=[
                    self.initial_setup.embedding_model_endpoint_dropdown,
                    self.initial_setup.vector_search_dropdown,
                    self.initial_setup.volume_dropdown,
                    self.initial_setup.intent_tabel_name_box,
                    self.initial_setup.prompt_tabel_name_box,
                    self.initial_setup.vector_search_index_box,
                ],
                outputs=[self.initial_setup.tab, self.instructions_tab.tab, self.tabs],
            )
            self.config_tab.save_config.click(
                save_config(False),
                show_progress="full",
                inputs=[
                    self.initial_setup.embedding_model_endpoint_dropdown,
                    self.initial_setup.vector_search_dropdown,
                    self.initial_setup.volume_dropdown,
                    self.initial_setup.intent_tabel_name_box,
                    self.initial_setup.prompt_tabel_name_box,
                    self.initial_setup.vector_search_index_box,
                ],
                outputs=[self.initial_setup.tab, self.instructions_tab.tab, self.tabs],
            )


            # Execute workflow when in batch mode
            self.batch_output_tab.execute.click(
                execute_workflow,
                inputs=[
                    self.code_explanation_tab.intent_system_prompt,
                    self.code_explanation_tab.intent_temperature,
                    self.code_explanation_tab.intent_max_tokens,
                    self.translation_tab.translation_system_prompt,
                    self.translation_tab.translation_temperature,
                    self.translation_tab.translation_max_tokens,
                ],
                outputs=self.batch_output_tab.run_status,
            )

            # produce preview when in interactive mode
            self.interactive_output_tab.produce_preview_button.click(
                produce_preview,
                inputs=[
                    self.code_explanation_tab.explained,
                    self.translation_tab.translated,
                    self.similar_code_tab.similar_code_notebook_url,
                ],
                outputs=self.interactive_output_tab.preview,
            )

            # write file to notebook when in interactive mode
            self.interactive_output_tab.write_to_workspace_button.click(
                fn=write_adhoc_to_workspace,
                inputs=[
                    self.interactive_output_tab.file_name,
                    self.interactive_output_tab.preview,
                    self.code_explanation_tab.intent_input_code,
                    self.code_explanation_tab.explained,
                ],
                outputs=self.interactive_output_tab.adhoc_write_output,
            )

        # collect all the input and output objects into a list to make it simpler to update them
        self.code_input_objects = [
            self.interactive_input_code_tab.interactive_code,
            self.batch_input_code_tab.selected_file,
            self.translation_tab.translation_input_code,
            self.code_explanation_tab.intent_input_code,
            self.similar_code_tab.similar_code_input,
        ]
        self.code_output_objects = [
            self.translation_tab.translated,
            self.similar_code_tab.similar_code_output,
        ]

        # add the button click logic
        with self.app:
            self.add_logic_loading_batch_mode()
            self.add_logic_loading_interactive_mode()
            self.change_tab_visibility()
            self.update_input_language()
            self.update_output_language()
            self.app.load()

    def add_logic_loading_batch_mode(self):

        def read_code_file_inner(volume_path, file_name):
            code = read_code_file(volume_path, file_name)
            return [code] * len(self.code_input_objects)

        self.batch_input_code_tab.select_code_file.select(
            fn=read_code_file_inner,
            inputs=[
                self.batch_input_code_tab.volume_path,
                self.batch_input_code_tab.select_code_file,
            ],
            outputs=self.code_input_objects,
        )

    def add_logic_loading_interactive_mode(self):

        def update_code(code):
            return [code] * len(self.code_input_objects)

        self.interactive_input_code_tab.interactive_code_button.click(
            fn=update_code,
            inputs=self.interactive_input_code_tab.interactive_code,
            outputs=self.code_input_objects,
        )

    def change_tab_visibility(self):
        for tab in [self.batch_input_code_tab, self.batch_output_tab]:
            self.instructions_tab.operation.change(
                lambda x: (gr.update(visible=(x != "Interactive mode"))),
                self.instructions_tab.operation,
                tab.tab,
            )
        for tab in [
            self.interactive_input_code_tab,
            self.interactive_output_tab,
            self.similar_code_tab,
        ]:
            self.instructions_tab.operation.change(
                lambda x: (gr.update(visible=(x == "Interactive mode"))),
                self.instructions_tab.operation,
                tab.tab,
            )
        for tab in [self.translation_tab, self.code_explanation_tab, self.config_tab]:
            self.instructions_tab.operation.change(
                lambda x: (gr.update(visible=True)),
                self.instructions_tab.operation,
                tab.tab,
            )

    def update_input_language(self):
        def inner(language):
            return [gr.update(language=language)] * len(self.code_input_objects)

        self.instructions_tab.input_language.input(
            fn=inner,
            inputs=self.instructions_tab.input_language,
            outputs=self.code_input_objects,
        )

    def update_output_language(self):
        def inner(language):
            return [gr.update(language=language)] * len(self.code_output_objects)

        self.instructions_tab.output_language.input(
            fn=inner,
            inputs=self.instructions_tab.output_language,
            outputs=self.code_output_objects,
        )
