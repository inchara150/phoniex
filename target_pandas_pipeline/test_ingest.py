from sqlalchemy import create_engine, text
from ingest import load_data

def test_guardrail_parity():
    # 1. Initialize Strict Database Environment
    engine = create_engine('sqlite:///:memory:')
    
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE employees (id INTEGER, name TEXT, joined_at TEXT)"))
        conn.commit()  # <-- This clears the autobegin transaction!
        
        # 2. Hardcoded Guardrail Transaction
        trans = conn.begin()
        try:
            load_data(conn)
            
            # 3. Verify absolute row-count parity
            result = conn.execute(text("SELECT COUNT(*) FROM employees")).scalar()
            assert result == 2, f"Data loss detected! Expected 2 rows, got {result}."
            
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise e