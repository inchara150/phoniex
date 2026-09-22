# Error handling guidelines

## KeyError on dictionaries
Never use bare `dict[key]` on external or config data. Use `dict.get(key, default)` or
raise a domain-specific `ConfigError` with the missing key in the message.

## TypeError and None values
Functions receiving optional arguments must check for `None` explicitly before arithmetic
or attribute access. Do not silence a TypeError with a broad `except Exception`.

## ZeroDivisionError
Guard divisions with an explicit check on the denominator and return a documented fallback
such as `0.0`. Never catch ZeroDivisionError just to hide a data bug.
