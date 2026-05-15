from typing import List, Dict, Generator
from openai import OpenAI
from core.llm_provider import LLMProvider

class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, messages: List[Dict[str, str]], temperature: float,
                 json_mode: bool = False) -> str:
        create_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        if json_mode:
            create_kwargs["response_format"] = {"type": "json_object"}
            
        response = self.client.chat.completions.create(**create_kwargs)
        return response.choices[0].message.content.strip()

    def stream(self, messages: List[Dict[str, str]], temperature: float
               ) -> Generator[str, None, None]:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=temperature
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
