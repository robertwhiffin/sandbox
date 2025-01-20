import gradio as gr
import pandas as pd

from sql_migration_assistant.config import get_config

config = get_config()


class PromptHelper:
    def __init__(self, schema, prompt_table):
        self.SCHEMA = schema
        self.PROMPT_TABLE = prompt_table

    def get_prompts(self, agent):
        gr.Info("Retrieving Prompts...")
        con = config.con
        response = pd.read_sql(
            f"SELECT promptID as id,"
            f"       agentConfigs.{agent}.system_prompt as prompt,"
            f"       agentConfigs.{agent}.temperature as temperature,"
            f"       agentConfigs.{agent}.max_tokens as token_limit,"
            f"       loadDatetime as save_time FROM {self.SCHEMA}.{self.PROMPT_TABLE} "
            f"WHERE map_keys(agentConfigs) = array('{agent}') "
            f"ORDER BY save_time DESC ",
            con=con,
        )
        return response

    def save_prompt(self, agent, prompt, temperature, token_limit):
        gr.Info("Saving prompt...")
        con = config.con
        cursor = con.cursor()
        agentConfig = f"MAP ('{agent}', MAP ('system_prompt', '{prompt}', 'temperature', '{temperature}', 'max_tokens', '{token_limit}'))"
        cursor.execute(
            f"INSERT INTO {self.SCHEMA}.{self.PROMPT_TABLE} "
            f"(promptID, agentConfigs, loadDatetime) "
            f"VALUES (hash(CURRENT_TIMESTAMP()), {agentConfig} ,CURRENT_TIMESTAMP())"
        )
        cursor.close()

        gr.Info("Prompt saved")
