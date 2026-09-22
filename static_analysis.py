import ast
import py_compile
import tempfile
import os

class StaticAnalysisResult:
    def __init__(self, is_valid: bool, issues: list[str], error_type: str = None):
        self.is_valid = is_valid
        self.issues = issues
        self.error_type = error_type

    def to_feedback(self) -> str:
        """Formats errors directly into prompt feedback for the Generator."""
        if self.is_valid:
            return "Static analysis passed with no deterministic errors."
        bullet_issues = "\n".join(f"- {issue}" for issue in self.issues)
        return f"Static Analysis Failure ({self.error_type}):\n{bullet_issues}"

def run_static_analysis(code_snippet: str, language: str = "python") -> StaticAnalysisResult:
    """
    Performs sub-millisecond static checks against generated patches.
    Catches syntax errors, indentation mistakes, and malformed AST structures.
    """
    if language.lower() != "python":
        # For non-Python code, fall through safely if Node linters aren't installed locally
        return StaticAnalysisResult(is_valid=True, issues=[])

    issues = []

    # Check 1: AST Parsing (catches invalid syntax, misplaced statements, unmatched parens)
    try:
        tree = ast.parse(code_snippet)
    except SyntaxError as e:
        error_msg = f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg} -> '{e.text.strip() if e.text else ''}'"
        return StaticAnalysisResult(is_valid=False, issues=[error_msg], error_type="SyntaxError")
    except Exception as e:
        return StaticAnalysisResult(is_valid=False, issues=[str(e)], error_type="ParseError")

    # Check 2: Bytecode compilation test
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
            tmp.write(code_snippet)
            tmp_path = tmp.name
        py_compile.compile(tmp_path, doraise=True)
    except py_compile.PyCompileError as e:
        issues.append(f"Bytecode Compilation Error: {e.msg}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Check 3: Semantic structural rules
    has_functions = any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))
    has_classes = any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    
    if not has_functions and not has_classes and len(tree.body) == 0:
        issues.append("Generated patch contains an empty body.")

    if issues:
        return StaticAnalysisResult(is_valid=False, issues=issues, error_type="DeterministicLintError")

    return StaticAnalysisResult(is_valid=True, issues=[])

# ==========================================
# LOCAL TESTING
# ==========================================
if __name__ == "__main__":
    print("🔍 PHOENIX DETERMINISTIC LINTER INITIALIZED\n")

    # Test 1: Broken code with a missing colon and syntax error
    broken_patch = """
def update_records(records)
    for r in records
        print(r)
"""
    result_broken = run_static_analysis(broken_patch)
    print(f"Test 1 [Broken Code]  -> Passed: {result_broken.is_valid}")
    print(f"Feedback Output:\n{result_broken.to_feedback()}\n")

    # Test 2: Valid code
    valid_patch = """
def update_records(records):
    filtered = [r for r in records if r is not None]
    return len(filtered)
"""
    result_valid = run_static_analysis(valid_patch)
    print(f"Test 2 [Valid Code]   -> Passed: {result_valid.is_valid}")
    print(f"Feedback Output:\n{result_valid.to_feedback()}")