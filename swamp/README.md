# Phoenix — Multi-Agent Specialist Swarm

Standalone swarm module with full offline test coverage via fakes.

## Structure

```
phoenix_contracts/   # Shared state schema, interfaces, fakes
swarm/
  supervisor.py      # Routes error trace to specialist
  agents/            # database, migration, security, general
  validators.py      # Per-agent output validation
  tools.py           # lint + sandbox wrappers
tests/               # Fully offline, fake LLM + sandbox
```

## Run Tests

```bash
pip install pytest
pytest tests/ -v
```

## Integration into brain.py

```python
from swarm.supervisor import supervisor_node
from swarm.agents.database import database_agent
from swarm.agents.migration import migration_agent
from swarm.agents.security import security_agent
from swarm.agents.general import general_agent

graph.add_node("supervisor", lambda s: supervisor_node(s, llm=real_llm))
graph.add_conditional_edges("supervisor", lambda s: s["route"], {
    "database":  "database_agent",
    "migration": "migration_agent",
    "security":  "security_agent",
    "general":   "general_agent",
})
```

Swap `FakeLLMClient` → real client. Everything else unchanged.
