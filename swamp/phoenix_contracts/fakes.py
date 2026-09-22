from .interfaces import LLMClient, SandboxRunner

class FakeLLMClient(LLMClient):
    def __init__(self, responses: dict):
        # key = substring of system prompt, value = canned response
        self._responses = responses

    def complete(self, system: str, user: str) -> str:
        for key, response in self._responses.items():
            if key in system:
                return response
        return "PATCH: # no-op"

class FakeSandbox(SandboxRunner):
    def run(self, code: str) -> dict:
        return {"stdout": "ok", "stderr": "", "exit_code": 0}
