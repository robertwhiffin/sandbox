import gradio as gr
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole


class LLMCalls:
    def __init__(self, workspace_client: WorkspaceClient):
        self.w = workspace_client

    def call_llm(self, messages, model_name, max_tokens, temperature):
        """
        Function to call the LLM model and return the response.
        :param messages: list of messages like
            messages=[
                       ChatMessage(role=ChatMessageRole.SYSTEM, content="You are an unhelpful assistant"),
                        ChatMessage(role=ChatMessageRole.USER, content="What is RAG?"),
                        ChatMessage(role=ChatMessageRole.ASSISTANT, content="A type of cloth?")
                    ]
        :return: the response from the model
        """
        print(f"Querying {model_name}")

        max_tokens = int(max_tokens)
        temperature = float(temperature)
        # check to make sure temperature is between 0.0 and 1.0
        if temperature < 0.0 or temperature > 1.0:
            raise gr.Error("Temperature must be between 0.0 and 1.0")
        response = self.w.serving_endpoints.query(
            name=model_name,
            max_tokens=max_tokens,
            messages=messages,
            temperature=temperature,
        )
        message = response.choices[0].message.content
        return message

    ################################################################################
    # FUNCTION FOR TRANSLATING CODE
    ################################################################################

    # this is called to actually send a request and receive response from the llm endpoint.

    def llm_translate(
        self, system_prompt, input_code, model_name, max_tokens, temperature
    ):
        messages = [
            ChatMessage(role=ChatMessageRole("system"), content=system_prompt),
            ChatMessage(role=ChatMessageRole("user"), content=input_code),
        ]

        # call the LLM end point.
        llm_answer = self.call_llm(
            messages=messages,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        translation = llm_answer
        return translation

    def llm_intent(
        self, system_prompt, input_code, model_name, max_tokens, temperature
    ):
        messages = [
            ChatMessage(role=ChatMessageRole("system"), content=system_prompt),
            ChatMessage(role=ChatMessageRole("user"), content=input_code),
        ]

        # call the LLM end point.
        llm_answer = self.call_llm(
            messages=messages,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        intend = llm_answer
        return intend
