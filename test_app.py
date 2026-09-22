import pytest
from app import get_user_config

def test_get_existing_key():
    config = {"app_name": "PhoenixDemo", "port": 8080}
    assert get_user_config(config, "port") == 8080

def test_get_missing_key_safe_default():
    config = {}
    result = get_user_config(config, "database_url")
    assert result is None, "Should safely return None for missing keys"
