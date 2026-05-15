import time
from typing import List, Dict, Generator
from core.llm_provider import LLMProvider

class LLMCaller:
    MAX_RETRIES = 2
    RETRY_DELAY = 2

    def __init__(self, llm_provider: LLMProvider):
        self.provider = llm_provider

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.0,
                 json_mode: bool = False) -> str:
        """Non-streaming call, useful for extraction."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return self.provider.complete(messages, temperature, json_mode)
            except Exception as e:
                if attempt == self.MAX_RETRIES:
                    raise TimeoutError(f"LLM call failed after {self.MAX_RETRIES + 1} attempts: {e}")
                print(f"[LLMCaller] Attempt {attempt + 1} failed: {e}. Retrying in {self.RETRY_DELAY}s...")
                time.sleep(self.RETRY_DELAY)

    def stream(self, messages: List[Dict[str, str]], temperature: float = 0.3
               ) -> Generator[str, None, None]:
        """Streaming call, useful for Q&A and chat."""
        yield from self.provider.stream(messages, temperature)
