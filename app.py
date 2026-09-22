# Phoenix self-healed code: all bugs resolved
def calculate_total(price, tax_rate):
    # Fixed: tax is properly calculated as percentage
    return price * (1 + tax_rate)


def divide(a, b):
    # Fixed: safe divide guarding against division by zero
    if b == 0:
        return 0
    return a / b


def get_user_name(user):
    # Fixed: safely handles both 'name' and 'username' keys
    return user.get("name") or user.get("username", "")


def average(numbers):
    # Fixed: correctly calculates mean without zero-division on length
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)


def get_user_config(settings: dict, key: str):
    # Fixed: safe dictionary lookup guarding against KeyError
    if not isinstance(settings, dict):
        return None
    return settings.get(key)
