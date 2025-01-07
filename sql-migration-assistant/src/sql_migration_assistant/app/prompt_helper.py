import gradio as gr

class PromptHelper:
    def __init__(self, see, catalog, schema, prompt_table, foundation_model_name):
        self.see = see
        self.CATALOG = catalog
        self.SCHEMA = schema
        self.PROMPT_TABLE = prompt_table
        self.FOUNDATION_MODEL_NAME = foundation_model_name

    def get_prompts(self, agent):
        gr.Info("Retrieving Prompts...")
        response = self.see.execute(
            f"SELECT promptID as id,"
            f"       agentConfigs.{agent}.system_prompt as prompt,"
            f"       agentConfigs.{agent}.temperature as temperature,"
            f"       agentConfigs.{agent}.max_tokens as token_limit,"
            f"       loadDatetime as save_time FROM {self.CATALOG}.{self.SCHEMA}.{self.PROMPT_TABLE} "
            f"WHERE map_keys(agentConfigs) = array('{agent}') "
            f"ORDER BY save_time DESC "
        )
        return response.result.data_array


    def save_prompt(self, agent, prompt, temperature, token_limit):
        gr.Info("Saving prompt...")
        agentConfig = f"MAP ('{agent}', MAP ('system_prompt', '{prompt}', 'temperature', '{temperature}', 'max_tokens', '{token_limit}'))"
        self.see.execute(
            f"INSERT INTO {self.CATALOG}.{self.SCHEMA}.{self.PROMPT_TABLE} "
            f"(promptID, agentConfigs, loadDatetime) "
            f"VALUES (hash(CURRENT_TIMESTAMP()), {agentConfig} ,CURRENT_TIMESTAMP())"
        )
        gr.Info("Prompt saved")
