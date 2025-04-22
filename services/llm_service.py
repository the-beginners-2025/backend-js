import enum
import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv
from openai import OpenAI


class Role(enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: Role
    content: str


class LLMService:
    def __init__(self, token: str, endpoint: str):
        self._client = OpenAI(
            api_key=token,
            base_url=endpoint,
        )

    def chat(self, model: str, messages: List[Message]) -> Message:
        response = self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": message.role.value, "content": message.content}
                for message in messages
            ],
            stream=False,
        )

        return Message(role=Role.ASSISTANT, content=response.choices[0].message.content)

    def chat_stream(self, model: str, messages: List[Message]):
        response = self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": message.role.value, "content": message.content}
                for message in messages
            ],
            stream=True,
        )

        for chunk in response:
            yield Message(role=Role.ASSISTANT, content=chunk.choices[0].delta.content)


if __name__ == "__main__":
    load_dotenv()
    llm_service = LLMService(
        token=os.getenv("LLM_TOKEN"),
        endpoint=os.getenv("LLM_ENDPOINT"),
    )

    messages = [
        Message(role=Role.SYSTEM, content="You are a helpful assistant."),
        Message(role=Role.USER, content="What is the capital of France?"),
    ]
    response = llm_service.chat(model=os.getenv("LLM_MODEL"), messages=messages)
    print(f"Assistant: {response.content}")
