from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> str: ...

class SandboxRunner(ABC):
    @abstractmethod
    def run(self, code: str) -> dict: ...
    # returns {"stdout": ..., "stderr": ..., "exit_code": int}
