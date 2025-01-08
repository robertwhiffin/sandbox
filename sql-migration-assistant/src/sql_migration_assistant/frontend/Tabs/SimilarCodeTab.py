import gradio as gr
from mlflow.protos.databricks_pb2 import visibility

from sql_migration_assistant.frontend.callbacks import similar_code_helper


class SimilarCodeTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Similar Code") as tab:
            self.tab = tab
            self.header = gr.Markdown(
                """
            ## Code with a similar intent to yours.
            
            This tab surfaces code that has a similar intent to input code. This can be used to understand whether 
            you need to migrate your code or if you can adapt and use the already migrated code. A link to the notebook you select as 
            most similar will be included in the output notebook from this workflow.
            
            Pressing the button below will retrieve the top 5 already processed code files with a similar intent to yours. 
            """
            )
            # a button
            self.find_similar_code = gr.Button("Retrieve similar code")
            # a row with an code and text box to show the similar code

            # create this hidden dataframe to store the returned code in
            with gr.Accordion(
                    label="## Retrieved Code - expand for details"
                    , open=False
                    , visible=False
            ) as self.retrieved_code:
                self.returned_code = gr.Dataframe(
                    visible=False
                    ,headers=["Code", "Intent", "Notebook URL", "Similarity", ]
                    ,type = "numpy"
                    , interactive=False
                )
            self.similar_code_notebook_url = gr.Text(
                  visible=False
            )
            self.similar_code_notebook_url_markdown = gr.Markdown(
                visible=False
            )
            # show the intent of the similar code
            self.similar_intent = gr.Textbox(
                label="Similar Code Intent."
                , interactive=False
                , visible=False
            )
            self.similar_code_selector = gr.Radio(
                label="Select retrieved code ranked by similarity - 1 is highest."
                ,choices=[1,2,3,4,5]
                ,type="index"
                ,value=1
                , visible=False
            )
            with gr.Row():
                self.similar_code_input = gr.Code(
                    label="Input Code.", language="sql"
                    ,interactive=False
                , visible=False
                )
                self.similar_code_output = gr.Code(
                    label="Similar code to yours.", language="sql"
                    , interactive=False
                , visible=False
                )


            def find_similar_code_action(input):
                '''
                This is the action that occurs when the "Retrieve similar code" button is clicked.
                It will
                - get the similar code from the vector search index
                - populate the results with the first value of the return boxes
                '''
                retrieved_similar_code = similar_code_helper.get_similar_code(input)
                similar_code=retrieved_similar_code[0][0]
                similar_intent=retrieved_similar_code[0][1]
                similar_notebook_url=retrieved_similar_code[0][2]
                similar_notebook_url_markdown = f"## [Link to similar code notebook]({similar_notebook_url})"
                return [retrieved_similar_code, similar_code, similar_intent, similar_notebook_url, similar_notebook_url_markdown]


            # When top button is clicked, get code and set everything to visible.
            self.find_similar_code.click(
                fn=find_similar_code_action,
                inputs=self.similar_code_input,
                outputs=[self.returned_code, self.similar_code_output
                    , self.similar_intent, self.similar_code_notebook_url
                         , self.similar_code_notebook_url_markdown]
            )

            self.find_similar_code.click(
                fn=lambda : [gr.update(visible=True)]*7,
                outputs=[
                         self.find_similar_code,
                         self.similar_intent,
                         self.similar_code_selector,
                         self.similar_code_input,
                         self.similar_code_output,
                         self.similar_code_notebook_url_markdown,
                         ],
            )
            # populate the intent and code of the selected similar code
            self.similar_code_selector.select(
                fn = lambda index, dataframe: [dataframe[index][0], dataframe[index][1]]
                ,inputs = [self.similar_code_selector, self.returned_code]
                ,outputs = [self.similar_code_output, self.similar_intent]
            )
            # populate the notebook url of the selected similar code
            self.similar_code_selector.select(
                fn = lambda index, dataframe: dataframe[index][2]
                ,inputs = [self.similar_code_selector, self.returned_code]
                ,outputs = [self.similar_code_notebook_url]
            )
