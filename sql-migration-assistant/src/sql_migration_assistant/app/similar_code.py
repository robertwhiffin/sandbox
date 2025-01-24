import gradio as gr
from databricks.sdk import WorkspaceClient


class SimilarCode:
    def __init__(
        self,
        workspace_client: WorkspaceClient,
        catalog_schema,
        code_intent_table_name,
        VS_index_name,
        VS_endpoint_name,
        warehouse_id
    ):
        self.w = workspace_client
        self.catalog_schema = catalog_schema
        # FQN = Fully Qualified Name
        self.code_intent_table_FQN = f"{catalog_schema}.{code_intent_table_name}"
        self.code_intent_table_name = code_intent_table_name
        self.vs_index_FQN = f"{catalog_schema}.{VS_index_name}"
        self.vs_endpoint_name = VS_endpoint_name
        self.warehouse_id = warehouse_id

    def save_intent(self, code, intent, url):
        code_hash = hash(code)
        catalog = self.catalog_schema.split(".")[0]
        schema = self.catalog_schema.split(".")[1]
        try:
            _ = self.w.statement_execution.execute_statement(
                statement=f'INSERT INTO {self.code_intent_table_name} VALUES ({code_hash}, "{code}", "{intent}", "{url}")',
                warehouse_id=self.warehouse_id
                , catalog=catalog
                , schema=schema
            )
        except Exception as e:
            raise gr.Error(f"Failed to save intent: {e}")

    def get_similar_code(self, intent):
        gr.Info("Retrieving similar code...")
        results = self.w.vector_search_indexes.query_index(
            index_name=f"{self.vs_index_FQN}",
            columns=["code", "intent", "notebook_url"],
            query_text=intent,
            num_results=5,
        )
        docs = results.result.data_array
        return docs

    def sync_index(self):
        self.w.vector_search_indexes.sync_index(index_name=self.vs_index_FQN)
