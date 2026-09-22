import re

def validate_patch(patch: str, route: str) -> bool:
    if not patch or len(patch.strip()) < 10:
        return False
    if route == "security":
        if re.search(r"(password|secret|api_key)\s*=\s*['\"].+['\"]", patch, re.I):
            return False
    return True
