import pandas as pd

def load_data(conn):
    df = pd.read_csv('data.csv')
    
    # Rename columns to match the database schema
    df.rename(columns={'emp_id': 'id', 'full_name': 'name', 'hire_date': 'joined_at'}, inplace=True)
    
    # Create the table if it does not exist
    create_table_query = """
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        joined_at DATE NOT NULL
    )
    """
    conn.execute(create_table_query)
    
    # Insert data into the table
    df.to_sql('employees', conn, if_exists='append', index=False)
    return len(df)
