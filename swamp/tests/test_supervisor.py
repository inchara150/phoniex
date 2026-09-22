import pytest
from phoenix_contracts.fakes import FakeLLMClient
from swarm.supervisor import supervisor_node

def test_routes_db_error(db_state, fake_llm):
    result = supervisor_node(db_state, llm=fake_llm)
    assert result["route"] == "database"

def test_invalid_route_falls_back_to_general(db_state):
    llm = FakeLLMClient({"routing agent": "nonsense_value"})
    result = supervisor_node(db_state, llm=llm)
    assert result["route"] == "general"

def test_route_key_present_in_result(db_state, fake_llm):
    result = supervisor_node(db_state, llm=fake_llm)
    assert "route" in result

def test_valid_routes_accepted(db_state):
    for valid_route in ["database", "migration", "security", "general"]:
        llm = FakeLLMClient({"routing agent": valid_route})
        result = supervisor_node(db_state, llm=llm)
        assert result["route"] == valid_route
