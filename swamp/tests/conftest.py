import pytest
from phoenix_contracts.fakes import FakeLLMClient, FakeSandbox
from phoenix_contracts.state import PhoenixState

@pytest.fixture
def db_state() -> PhoenixState:
    return PhoenixState(
        error_trace="psycopg2.OperationalError: connection refused",
        target_function="def get_user(id): return db.query(User).get(id)",
        generated_patch=None,
        route=None,
        retrieved_chunks=[],
        specialist_output=None,
        validation_passed=False,
        gco2_estimate=0.0
    )

@pytest.fixture
def migration_state() -> PhoenixState:
    return PhoenixState(
        error_trace="alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'",
        target_function="def upgrade(): op.add_column('users', sa.Column('email', sa.String()))",
        generated_patch=None,
        route=None,
        retrieved_chunks=[],
        specialist_output=None,
        validation_passed=False,
        gco2_estimate=0.0
    )

@pytest.fixture
def security_state() -> PhoenixState:
    return PhoenixState(
        error_trace="ValueError: raw SQL interpolation detected",
        target_function="def get_user(name): return db.execute(f'SELECT * FROM users WHERE name={name}')",
        generated_patch=None,
        route=None,
        retrieved_chunks=[],
        specialist_output=None,
        validation_passed=False,
        gco2_estimate=0.0
    )

@pytest.fixture
def fake_llm():
    return FakeLLMClient({
        "routing agent": "database",
        "Database specialist": "def get_user(id):\n    with db.session() as s:\n        return s.get(User, id)",
        "Alembic migration": "def upgrade():\n    op.add_column('users', sa.Column('email', sa.String(), nullable=True))",
        "Security auditor": "def get_user(name):\n    return db.execute('SELECT * FROM users WHERE name=:n', {'n': name})\n# CVE: SQL-INJECTION-001",
        "general-purpose": "def get_user(id):\n    return db.session.get(User, id)",
    })

@pytest.fixture
def fake_sandbox():
    return FakeSandbox()
