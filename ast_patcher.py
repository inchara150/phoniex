import ast
import re

def sanitize_code(raw_text: str) -> str:
    """Strips conversational text and extracts code inside markdown fences."""
    match = re.search(
        r"```(?:python)?\s*\n(.*?)```",
        raw_text,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return raw_text.strip()


def get_function_line_numbers(source_code: str, function_name: str):
    """Parses code into an AST and finds line boundaries for a target function."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        print(f"❌ Syntax error during AST parse: {e}")
        return None, None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                start_line = node.lineno

                # Include decorators in the replacement range
                if node.decorator_list:
                    start_line = node.decorator_list[0].lineno

                return start_line, node.end_lineno

    return None, None


def surgical_patch(
    original_code: str,
    llm_patch: str,
    target_function: str,
) -> str:
    """
    Safely extracts and splices the target function
    without altering surrounding file content.
    """
    if not isinstance(original_code, str) or not original_code:
        return llm_patch or ""
    clean_patch = sanitize_code(llm_patch)

    # Find target function in original source
    orig_start, orig_end = get_function_line_numbers(
        original_code,
        target_function,
    )

    if orig_start is None or orig_end is None:
        print(
            f"⚠️ Target function '{target_function}' "
            "not found in original code. Aborting."
        )
        return original_code

    # Find target function in LLM-generated patch
    patch_start, patch_end = get_function_line_numbers(
        clean_patch,
        target_function,
    )

    if patch_start is None or patch_end is None:
        print(
            f"⚠️ Target function '{target_function}' "
            "not found in LLM patch. Aborting."
        )
        return original_code

    orig_lines = original_code.splitlines()
    patch_lines = clean_patch.splitlines()

    # Extract only the target function
    fixed_function_block = patch_lines[patch_start - 1 : patch_end]

    # Replace original function while preserving everything else
    new_file_lines = (
        orig_lines[: orig_start - 1]
        + fixed_function_block
        + orig_lines[orig_end:]
    )

    return "\n".join(new_file_lines)


if __name__ == "__main__":
    original = """import pandas as pd

# System Metadata

class Storage:
    pass

def load_data(conn):
    return 0

def keep_me():
    return True
"""

    llm_output = '''Here is the fix:
```python
def load_data(conn):
    df = pd.read_csv("data.csv")
    return len(df)
```'''

    result = surgical_patch(
        original,
        llm_output,
        "load_data",
    )

    print("Patched Code:\n")
    print(result)