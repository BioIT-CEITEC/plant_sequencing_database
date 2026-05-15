from abc import ABC, abstractmethod
from typing import Generator, List, Dict

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: List[Dict[str, str]], temperature: float,
                 json_mode: bool = False) -> str:
        """Execute a non-streaming LLM call."""
        pass

    @abstractmethod
    def stream(self, messages: List[Dict[str, str]], temperature: float
               ) -> Generator[str, None, None]:
        """Execute a streaming LLM call, yielding string chunks."""
        pass
