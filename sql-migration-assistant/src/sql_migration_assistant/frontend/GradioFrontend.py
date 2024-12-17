import gradio as gr
from pyarrow import output_stream

from sql_migration_assistant.frontend.Tabs.BatchInputCodeTab import BatchInputCodeTab
from sql_migration_assistant.frontend.Tabs.BatchOutputTab import BatchOutputTab
from sql_migration_assistant.frontend.Tabs.CodeExplanationTab import CodeExplanationTab
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
    exectute_workflow,
    save_intent_wrapper,
)


class GradioFrontend:
    intro = """<img align="right" src="https://asset.brandfetch.io/idSUrLOWbH/idm22kWNaH.png" alt="logo" width="120">

# Databricks Legion Migration Accelerator
"""

    def __init__(self):
        with gr.Blocks(theme=gr.themes.Soft()) as self.app:
            self.intro_markdown = gr.Markdown(self.intro)
            self.instructions_tab = InstructionsTab()

            self.interactive_input_code_tab = InteractiveInputCodeTab()
            self.batch_input_code_tab = BatchInputCodeTab()
            self.code_explanation_tab = CodeExplanationTab()
            self.translation_tab = TranslationTab()
            self.similar_code_tab = SimilarCodeTab()
            self.batch_output_tab = BatchOutputTab()
            self.interactive_output_tab = InteractiveOutputTab()

            self.batch_output_tab.execute.click(
                exectute_workflow,
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
            self.interactive_output_tab.produce_preview_button.click(
                produce_preview,
                inputs=[
                    self.code_explanation_tab.explained,
                    self.translation_tab.translated,
                ],
                outputs=self.interactive_output_tab.preview,
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
            self.change_tabs_based_on_operation_mode()
            self.update_input_language()
            self.update_output_language()

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

    def change_tabs_based_on_operation_mode(self):
        for tab in [self.batch_input_code_tab, self.batch_output_tab]:
            self.instructions_tab.operation.change(
                lambda x: (gr.update(visible=(x != "Interactive mode"))),
                self.instructions_tab.operation,
                tab.tab,
            )
        for tab in [self.interactive_input_code_tab, self.interactive_output_tab]:
            self.instructions_tab.operation.change(
                lambda x: (gr.update(visible=(x == "Interactive mode"))),
                self.instructions_tab.operation,
                tab.tab,
            )

    def update_input_language(self):
        def inner(language):
            return [gr.update(language=language)] * len(self.code_input_objects)
        self.instructions_tab.input_language.input(
            fn=inner,
            inputs=self.instructions_tab.input_language,
            outputs= self.code_input_objects
        )


    def update_output_language(self):
        def inner(language):
            return [gr.update(language=language)] * len(self.code_output_objects)
        self.instructions_tab.output_language.input(
            fn=inner,
            inputs=self.instructions_tab.output_language,
            outputs= self.code_output_objects
        )