# Databricks notebook source
import base64
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat, Language
from pyspark.sql import functions as f
from pyspark.sql.types import *
import json

# COMMAND ----------

# DBTITLE 1,get params into notebook
agent_configs = json.loads(dbutils.widgets.get("agent_configs"))
app_configs = json.loads(dbutils.widgets.get("app_configs"))

secret_scope = app_configs["DATABRICKS_TOKEN_SECRET_SCOPE"]
secret_key = app_configs["DATABRICKS_TOKEN_SECRET_KEY"]
host = app_configs["DATABRICKS_HOST"]

workspace_location = app_configs["WORKSPACE_LOCATION"]
workspace_location = "/Workspace" + workspace_location

key = dbutils.secrets.get(scope=secret_scope, key=secret_key)

# COMMAND ----------

# DBTITLE 1,extract relevant variables from params

silver_llm_responses = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.silver_llm_responses'
)
gold_table = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.gold_transformed_notebooks'
)

code_intent_table = f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.{app_configs["CODE_INTENT_TABLE_NAME"]}'

prompt_id = dbutils.jobs.taskValues.get(taskKey="ingest_to_holding", key="promptID")
output_volume_path = app_configs["VOLUME_NAME_OUTPUT_PATH"]


# COMMAND ----------

# DBTITLE 1,function to write out a notebook as a string


@udf(StringType())
def write_notebook_code(llm_responses, similar_code):
    if similar_code is not None:
        return write_notebook_code_with_similarity(llm_responses, similar_code)
    else:
        return write_notebook_code_without_similarity(llm_responses)


def write_notebook_code_with_similarity(llm_responses, similar_code):
    # parse the llm responses to get the explanation and translation
    for response in llm_responses:
        if "explanation_agent" == response[0]:
            explanation = response[1]
        elif "translation_agent" == response[0]:
            translated_code = response[1]
    # parse the similar code into a nice format
    # looks like [[url, similarity], ...]
    # want to present it as a markdown table

    table_header = """
-- MAGIC | Notebook URL | Notebook Description | Similarity Score |
-- MAGIC |--------------|----------------------|------------------|
"""
    table_rows = "\n".join(
        [f"-- MAGIC | [Link]({item[0]}) |{item[1]} | {str(round(float(item[2]), 3))} |" for item in similar_code]
    )
    markdown_table = table_header + table_rows

    template = """
-- Databricks notebook source
-- MAGIC %md
-- MAGIC # This notebook was AI generated. AI can make mistakes. This is provided as a tool to accelerate your migration. 
-- MAGIC
-- MAGIC ### AI Detected Similar Code 
-- MAGIC The table below shows gives the top 5 most similar notebooks to this one.
SIMILAR_CODE_NOTEBOOKS
-- MAGIC 
-- MAGIC ### AI Generated Intent
-- MAGIC
-- MAGIC INTENT_GOES_HERE

-- COMMAND ----------

TRANSLATED_CODE_GOES_HERE
  """.strip()

    output = (
        template
        .replace("INTENT_GOES_HERE", explanation)
        .replace("TRANSLATED_CODE_GOES_HERE", translated_code)
        .replace("SIMILAR_CODE_NOTEBOOKS", markdown_table)
    )
    return output


def write_notebook_code_without_similarity(llm_responses):
    # parse the llm responses to get the explanation and translation
    for response in llm_responses:
        if "explanation_agent" == response[0]:
            explanation = response[1]
        elif "translation_agent" == response[0]:
            translated_code = response[1]

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

    output = (
        template
        .replace("INTENT_GOES_HERE", explanation)
        .replace("TRANSLATED_CODE_GOES_HERE", translated_code)
    )
    return output


# COMMAND ----------

# DBTITLE 1,write the notebooks into a new column
gold_df = (
    spark.read.table(silver_llm_responses)
    .filter(f.col("promptID") == f.lit(prompt_id))
    .withColumn("agentResponses", f.struct(f.col("agentName"), f.col("agentResponse")))
    .groupBy(f.col("content"), f.col("processedDateString"), f.col("promptID"), f.col("path"),
             f.col("outputNotebookPath"))
    .agg(
        f.collect_list(f.col("agentResponses")).alias("agentResponses"),
        f.first(f.col('similarCodeNotebooks'), ignorenulls=True).alias("similarCodeNotebooks"),
    )
    .withColumn("notebookAsString", write_notebook_code(f.col("agentResponses"), f.col("similarCodeNotebooks")))
    .withColumn("agentResponses", f.map_from_entries(f.col("agentResponses")))
    .withColumn(
        "outputVolumePath",
        f.concat_ws(
            "/", f.lit(output_volume_path), f.col("processedDateString"), f.col("path")
        ),
    )
    .select(
        "promptID",
        "content",
        "processedDateString",
        "notebookAsString",
        "outputVolumePath",
        "outputNotebookPath",
        "similarCodeNotebooks",
        "agentResponses"
    )
)

gold_df.display()

# COMMAND ----------

temp_table_name = "gold_temp"
gold_df.createOrReplaceTempView(temp_table_name)
spark.sql(
    f"""
  INSERT INTO {gold_table} TABLE {temp_table_name}
  """
)
display(
    spark.sql(
        f"""
  select * from {gold_table}
  """
    )
)

# COMMAND ----------


pandas_gold = gold_df.toPandas()

w = WorkspaceClient(host=host, token=key)


def write_files(row):
    volume_path = row["outputVolumePath"]
    content = row["notebookAsString"]
    # write to a volume
    dbutils.fs.put(volume_path, content)

    # write to workspace

    notebook_path = row["outputNotebookPath"]
    notebook_path_root = "/".join(notebook_path.split("/")[:-1])
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
    return url


pandas_gold = gold_df.toPandas()
pandas_gold["notebook_url"] = pandas_gold.apply(write_files, axis=1)
pandas_gold

# COMMAND ----------

df = spark.createDataFrame(pandas_gold)
df.createOrReplaceTempView("code_intent_updates")

spark.sql(
    f"""
MERGE INTO {code_intent_table} AS target
USING (
  SELECT hash(content) AS id
  , content AS code
  , agentResponses.explanation_agent AS intent
  , notebook_url AS notebook_url
  FROM code_intent_updates
) AS source
ON target.id = source.id
WHEN MATCHED THEN
  UPDATE SET target.code = source.code, target.intent = source.intent, target.notebook_url = source.notebook_url
WHEN NOT MATCHED THEN
  INSERT (id, code, intent, notebook_url) VALUES (source.id, source.code, source.intent, source.notebook_url)
"""
)