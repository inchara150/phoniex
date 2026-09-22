import ast
from phoenix_contracts.interfaces import SandboxRunner

def lint_patch(patch: str) -> list:
    try:
        ast.parse(patch)
        return []
    except SyntaxError as e:
        return [str(e)]

def sandbox_patch(patch: str, runner: SandboxRunner) -> dict:
    return runner.run(patch)
