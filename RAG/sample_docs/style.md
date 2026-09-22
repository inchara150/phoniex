# Code style

## Patches
Patches must keep the function signature and docstring unchanged. Do not add new
third-party dependencies. Keep changes minimal and preserve existing comments.

## Logging
Use the module-level `logger`; never `print()` in library code.
