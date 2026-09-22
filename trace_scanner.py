import re

class TraceScanner:
    def __init__(self):
        # Maps Python exception types to the scheduler's bug taxonomy
        self.taxonomy_map = {
            "SyntaxError": "syntax",
            "IndentationError": "syntax",
            "TabError": "syntax",
            "OperationalError": "db_deadlock",
            "IntegrityError": "db_deadlock",
            "IndexError": "algorithm",
            "KeyError": "algorithm",
            "ValueError": "algorithm",
            "TypeError": "algorithm"
        }

    def scan_traceback(self, raw_trace: str) -> dict:
        """
        Parses a raw Python traceback to extract the critical metadata 
        required by the AST Patcher and the Scheduler.
        """
        # Default fallback values
        result = {
            "file_path": None,
            "target_function": None,
            "error_type": "UnknownError",
            "error_message": "",
            "bug_type": "algorithm" # Default to algorithm if unknown
        }

        if not raw_trace:
            return result

        lines = raw_trace.strip().splitlines()
        
        # 1. Extract Error Type and Message (Usually the very last line)
        last_line = lines[-1]
        error_match = re.match(r"^([\w\.]+):\s*(.*)", last_line)
        if error_match:
            # E.g., sqlalchemy.exc.OperationalError -> OperationalError
            full_error_type = error_match.group(1).split('.')[-1]
            result["error_type"] = full_error_type
            result["error_message"] = error_match.group(2).strip()
            
            # Map to scheduler taxonomy
            result["bug_type"] = self.taxonomy_map.get(full_error_type, "algorithm")

        # 2. Extract File Path and Target Function 
        # We look for the LAST occurrence of 'File "...", line X, in <function>' 
        # because the bottom of the stack trace is where the actual crash occurred.
        frame_pattern = re.compile(r'\s*File\s+"([^"]+)",\s*line\s*(\d+),\s*in\s+(.+)')
        
        for line in reversed(lines):
            frame_match = frame_pattern.match(line)
            if frame_match:
                result["file_path"] = frame_match.group(1)
                # If the crash is at the module level, Python uses <module>
                func_name = frame_match.group(3)
                result["target_function"] = func_name if func_name != "<module>" else "global_scope"
                break
                
        return result

# ==========================================
# LOCAL TESTING
# ==========================================
if __name__ == "__main__":
    scanner = TraceScanner()

    # Simulated crash log 1: Database Issue
    trace_1 = """Traceback (most recent call last):
  File "app/api.py", line 45, in <module>
    process_queue()
  File "app/database/ingest.py", line 112, in update_records
    session.commit()
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked
"""

    # Simulated crash log 2: Syntax Issue
    trace_2 = """Traceback (most recent call last):
  File "server.py", line 10, in start_server
    app.run(port=8080
SyntaxError: unexpected EOF while parsing
"""

    print("🔍 INITIATING STACK TRACE SCANNER\n")

    print("[TEST 1] Complex DB Deadlock Trace:")
    res_1 = scanner.scan_traceback(trace_1)
    for key, val in res_1.items():
        print(f"  ↳ {key.ljust(16)}: {val}")

    print("\n[TEST 2] Standard Syntax Error Trace:")
    res_2 = scanner.scan_traceback(trace_2)
    for key, val in res_2.items():
        print(f"  ↳ {key.ljust(16)}: {val}")