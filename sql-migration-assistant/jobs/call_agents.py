# Databricks notebook source
# MAGIC %pip install databricks-sdk --upgrade

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import json
import os
from pyspark.sql.types import (
    ArrayType,
    StructType,
    StructField,
    StringType,
    MapType,
    IntegerType,
    TimestampType,
    DoubleType,
)
import pyspark.sql.functions as f
from pyspark.sql.functions import udf, pandas_udf

# COMMAND ----------


agent_configs = json.loads(dbutils.widgets.get("agent_configs"))
app_configs = json.loads(dbutils.widgets.get("app_configs"))
record_id = dbutils.widgets.get("record_id")

bronze_holding_table = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.bronze_holding_table'
)
silver_llm_responses = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.silver_llm_responses'
)
code_intent_table = f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.{app_configs["CODE_INTENT_TABLE_NAME"]}'

secret_scope = app_configs["DATABRICKS_TOKEN_SECRET_SCOPE"]
secret_key = app_configs["DATABRICKS_TOKEN_SECRET_KEY"]
DATABRICKS_HOST = app_configs["DATABRICKS_HOST"]

workspace_location = app_configs["WORKSPACE_LOCATION"]

# get the processedDatetime value set in the first task
processedDatetime = dbutils.jobs.taskValues.get(taskKey="ingest_to_holding", key="processedDatetime",
                                                debugValue="2023-0-4")

# COMMAND ----------

print(record_id)

# COMMAND ----------

# need this for when workspace client is created during a job
DATABRICKS_PAT = dbutils.secrets.get(scope=secret_scope, key=secret_key)

####################
# udf to get the most similar code notebook path
VS_INDEX_NAME = app_configs["VS_INDEX_NAME"]
catalog = app_configs["CATALOG"]
schema = app_configs["SCHEMA"]

w = WorkspaceClient(host=DATABRICKS_HOST, token=DATABRICKS_PAT)


def get_similar_code(row):
    agent = row['agentName']
    if agent == "explanation_agent":
        intent = row["agentResponse"]
        results = w.vector_search_indexes.query_index(
            index_name=f"{catalog}.{schema}.{VS_INDEX_NAME}",
            columns=["notebook_url", "intent"],
            query_text=intent,
            num_results=5,
        )
        data_array = results.result.data_array
        if data_array:
            row['similarCodeNotebooks'] = [{"notebook_url": item[0], "intent": item[1], "similarity": item[2]} for item
                                           in data_array]
            return row
        else:
            row['similarCodeNotebooks'] = None
            return row
    else:
        row['similarCodeNotebooks'] = None
        return row


def process_row(row):
    input_code, agent_configs = row["content"], row["agentConfigs"]
    output = {}
    for agent in agent_configs.keys():
        agent_app_configs = agent_configs[agent]
        system_prompt = agent_app_configs["system_prompt"]
        endpoint = agent_app_configs["endpoint"]
        max_tokens = agent_app_configs["max_tokens"]
        temperature = agent_app_configs["temperature"]
        messages = [
            ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=ChatMessageRole.USER, content=input_code),
        ]
        max_tokens = int(max_tokens)
        temperature = float(temperature)
        try:
            response = w.serving_endpoints.query(
                name=endpoint,
                max_tokens=max_tokens,
                messages=messages,
                temperature=temperature,
            )
            message = response.choices[0].message.content
            row['agentName'] = agent
            row['agentResponse'] = message
        except TimeoutError:
            row['agentName'] = agent
            row['agentResponse'] = "Request timeout. Reduce size of input code."

    return row


# COMMAND ----------

local_data = (
    spark.read.table(bronze_holding_table)
    .where(f.col("id") == f.lit(record_id))
    .collect()[0].asDict()
)


# COMMAND ----------

def build_output(local_data):
    output = process_row(local_data)
    output = get_similar_code(output)
    output['processedDateString'] = processedDatetime
    output["outputNotebookPath"] = '/'.join(
        [workspace_location, "outputNotebooks", "batchTranslated", processedDatetime, output['path']])
    return output


processed = build_output(local_data)

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType, DoubleType

schema = StructType([
    StructField("path", StringType(), True),
    StructField("promptID", IntegerType(), True),
    StructField("processedDateString", StringType(), True),
    StructField("content", StringType(), True),
    StructField("agentName", StringType(), True),
    StructField("agentResponse", StringType(), True),
    StructField("outputNotebookPath", StringType(), True),
    StructField("similarCodeNotebooks", ArrayType(
        StructType([
            StructField("notebook_url", StringType(), True),
            StructField("intent", StringType(), True),
            StructField("similarity", DoubleType(), True)
        ])
    ), True)
])

# COMMAND ----------

# convert the dictionary processed to a spark dataframe
processed_df = (
    spark.createDataFrame([processed], schema=schema)
    .select("path", "promptID", "processedDateString", "content", "agentName", "agentResponse", "outputNotebookPath",
            'similarCodeNotebooks')
)
display(processed_df)

# COMMAND ----------

(processed_df.write.mode("append").saveAsTable(silver_llm_responses))

# COMMAND ----------

