import pytest
from swarm.agents.database import database_agent
from swarm.agents.migration import migration_agent
from swarm.agents.security import security_agent
from swarm.agents.general import general_agent
from swarm.validators import validate_patch
from swarm.tools import lint_patch, sandbox_patch

def test_db_agent_produces_patch(db_state, fake_llm):
    result = database_agent(db_state, llm=fake_llm)
    assert result["generated_patch"] is not None
    assert result["specialist_output"] == result["generated_patch"]
    assert validate_patch(result["generated_patch"], route="database")

def test_migration_agent_produces_patch(migration_state, fake_llm):
    result = migration_agent(migration_state, llm=fake_llm)
    assert result["generated_patch"] is not None
    assert validate_patch(result["generated_patch"], route="migration")

def test_security_agent_produces_patch(security_state, fake_llm):
    result = security_agent(security_state, llm=fake_llm)
    assert result["generated_patch"] is not None
    assert validate_patch(result["generated_patch"], route="security")

def test_security_validator_rejects_raw_secret():
    bad_patch = "def login():\n    password = 'supersecret123'\n    return True"
    assert not validate_patch(bad_patch, route="security")

def test_lint_clean_patch():
    clean = "def foo():\n    return 42"
    assert lint_patch(clean) == []

def test_lint_broken_patch():
    broken = "def foo(\n    return 42"
    assert len(lint_patch(broken)) > 0

def test_sandbox_runs(fake_sandbox):
    result = sandbox_patch("def foo(): pass", fake_sandbox)
    assert result["exit_code"] == 0

def test_general_agent_produces_patch(db_state, fake_llm):
    result = general_agent(db_state, llm=fake_llm)
    assert result["generated_patch"] is not None
