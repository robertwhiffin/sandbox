import base64
import datetime
import json
import os

import gradio as gr
from databricks.sdk.service.workspace import ImportFormat, Language

from sql_migration_assistant.app.llm import LLMCalls
from sql_migration_assistant.app.prompt_helper import PromptHelper
from sql_migration_assistant.app.similar_code import SimilarCode
from sql_migration_assistant.config import get_config

config = get_config()
w = config.w

llm = LLMCalls(w)

prompt_helper = PromptHelper(
    catalog_schema=config.catalog_schema, prompt_table=config.get("PROMPT_TABLE")
)
similar_code_helper = SimilarCode(
    workspace_client=w,
    catalog_schema=config.catalog_schema,
    code_intent_table_name=config.get("CODE_INTENT_TABLE_NAME"),
    VS_index_name=config.get("VS_INDEX_NAME"),
    VS_endpoint_name=config.get("VECTOR_SEARCH_ENDPOINT_NAME"),
)


def list_files(path_to_volume):
    file_infos = w.dbutils.fs.ls(path_to_volume)
    file_names = [x.name for x in file_infos]
    file_name_radio = gr.Radio(label="Select Code File", choices=file_names)
    return file_name_radio


def make_status_box_visible():
    return gr.Markdown(label="Job Run Status Page", visible=True)


def read_code_file(volume_path, file_name):
    file_name = os.path.join(volume_path, file_name)
    file = w.files.download(file_name)
    code = file.contents.read().decode("utf-8")
    return code


def llm_intent_wrapper(system_prompt, input_code, model_name, max_tokens, temperature):
    model_name = model_name if not model_name.startswith("PPT - ") else model_name[6:]
    intent = llm.llm_intent(
        system_prompt, input_code, model_name, max_tokens, temperature
    )
    return intent


def llm_translate_wrapper(
    system_prompt, input_code, model_name, max_tokens, temperature
):
    model_name = model_name if not model_name.startswith("PPT - ") else model_name[6:]
    translated_code = llm.llm_translate(
        system_prompt, input_code, model_name, max_tokens, temperature
    )
    return translated_code


def produce_preview(explanation, translated_code, similar_code_notebook_url):
    if similar_code_notebook_url:
        template = """
-- Databricks notebook source
-- MAGIC %md
-- MAGIC # This notebook was AI generated. AI can make mistakes. This is provided as a tool to accelerate your migration. 
-- MAGIC
-- MAGIC ### AI Detected Similar Code 
-- MAGIC 
-- MAGIC [This](SIMILAR_CODE_NOTEBOOK_URL)) is the most similar notebook to the code you provided and may provide additional context and assistance for finetuning this output.
-- MAGIC 
-- MAGIC ### AI Generated Intent
-- MAGIC
-- MAGIC INTENT_GOES_HERE


-- COMMAND ----------

TRANSLATED_CODE_GOES_HERE
        """.strip()
        preview_code = (
            template.replace("INTENT_GOES_HERE", explanation)
            .replace("TRANSLATED_CODE_GOES_HERE", translated_code)
            .replace("SIMILAR_CODE_NOTEBOOK_URL", similar_code_notebook_url)
        )
        return preview_code
    else:
        gr.Info("Similar code not provided. Did you mean to use the Similar Code tab?")
        template = """
-- Databricks notebook source
-- MAGIC %md
-- MAGIC # This notebook was AI generated. AI can make mistakes. This is provided as a tool to accelerate your migration. 
-- MAGIC
-- MAGIC ### AI Generated Intent
-- MAGIC
-- MAGIC INTENT_GOES_HERE


-- COMMAND ----------

TRANSLATED_CODE_GOES_HERE
        """.strip()
        preview_code = template.replace("INTENT_GOES_HERE", explanation).replace(
            "TRANSLATED_CODE_GOES_HERE", translated_code
        )
        return preview_code


def write_adhoc_to_workspace(file_name, preview, input_code, explained):
    if len(file_name) == 0:
        raise gr.Error("Please provide a filename")
    WORKSPACE_LOCATION = config.get_workspace_path()
    notebook_path_root = f"{WORKSPACE_LOCATION}/outputNotebooks/manuallyTranslated/{str(datetime.datetime.now().date()).replace(':', '_')}"
    notebook_path = f"{notebook_path_root}/{file_name}"
    content = preview
    w.workspace.mkdirs(notebook_path_root)
    w.workspace.import_(
        content=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        path=notebook_path,
        format=ImportFormat.SOURCE,
        language=Language.SQL,
        overwrite=True,
    )
    _ = w.workspace.get_status(notebook_path)
    id = _.object_id
    url = f"{w.config.host}/#notebook/{id}"
    output_message = f"Notebook {file_name} written to Databricks [here]({url})"

    # save the intent at the same time
    if explained:
        similar_code_helper.save_intent(input_code, explained, url)
        similar_code_helper.sync_index()

    return output_message


def execute_workflow(
    intent_prompt,
    intent_temperature,
    intent_max_tokens,
    translation_prompt,
    translation_temperature,
    translation_max_tokens,
):
    gr.Info("Beginning code transformation workflow")
    agent_config_payload = [
        [
            {
                "translation_agent": {
                    "system_prompt": translation_prompt,
                    "endpoint": config.get("TRANSLATION_MODEL_NAME"),
                    "max_tokens": translation_max_tokens,
                    "temperature": translation_temperature,
                }
            }
        ],
        [
            {
                "explanation_agent": {
                    "system_prompt": intent_prompt,
                    "endpoint": config.get("INTENT_MODEL_NAME"),
                    "max_tokens": intent_max_tokens,
                    "temperature": intent_temperature,
                }
            }
        ],
    ]
    WORKSPACE_LOCATION = config.get_workspace_path()

    app_config_payload = {
        "VOLUME_NAME_OUTPUT_PATH": config.get("VOLUME_NAME_OUTPUT_PATH"),
        "VOLUME_NAME_INPUT_PATH": config.get("VOLUME_NAME_INPUT_PATH"),
        "VOLUME_NAME_CHECKPOINT_PATH": config.get("VOLUME_NAME_CHECKPOINT_PATH"),
        "CATALOG": config.get("CATALOG"),
        "SCHEMA": config.get("SCHEMA"),
        "DATABRICKS_HOST": w.config.host,
        "DATABRICKS_TOKEN_SECRET_SCOPE": config.get("DATABRICKS_TOKEN_SECRET_SCOPE"),
        "DATABRICKS_TOKEN_SECRET_KEY": config.get("DATABRICKS_TOKEN_SECRET_KEY"),
        "CODE_INTENT_TABLE_NAME": config.get("CODE_INTENT_TABLE_NAME"),
        "VS_INDEX_NAME": config.get("VS_INDEX_NAME"),
        "WORKSPACE_LOCATION": WORKSPACE_LOCATION,
    }

    app_configs = json.dumps(app_config_payload)
    agent_configs = json.dumps(agent_config_payload)

    TRANSFORMATION_JOB_ID = config.get("TRANSFORMATION_JOB_ID")
    response = w.jobs.run_now(
        job_id=int(TRANSFORMATION_JOB_ID),
        job_parameters={
            "agent_configs": agent_configs,
            "app_configs": app_configs,
        },
    )
    run_id = response.run_id

    job_url = f"{w.config.host}/jobs/{TRANSFORMATION_JOB_ID}"
    textbox_message = (
        f"Job run initiated. Click [here]({job_url}) to view the job status. "
        f"You just executed the run with run_id: {run_id}\n"
        f"Output notebooks will be written to the Workspace for immediate use at *{WORKSPACE_LOCATION}/outputNotebooks/batchTranslated*"
        f", and also in the *Output Code* folder in the UC Volume [here]({w.config.host}/explore/data/volumes/{w.catalogs}/{config.get('SCHEMA')}/{config.get('VOLUME')})"
    )
    return textbox_message


# retreive the row from the table and populate the system prompt, temperature, and max tokens
def get_prompt_details(prompt_id, prompts):
    prompt = prompts[prompts["id"] == prompt_id]
    return [
        prompt["Prompt"].values[0],
        prompt["Temperature"].values[0],
        prompt["Max Tokens"].values[0],
    ]
