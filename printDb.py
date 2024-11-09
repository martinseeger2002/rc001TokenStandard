import sqlite3

def read_database(db_name):
    # Connect to the SQLite database
    db_path = f'./db/{db_name}.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to select all records from the items table
    cursor.execute('SELECT * FROM items')

    # Fetch all rows from the executed query
    rows = cursor.fetchall()

    # Print the column names
    column_names = [description[0] for description in cursor.description]
    print(f"Columns: {column_names}")

    # Print each row
    for row in rows:
        print(row)

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    # Replace 'your_db_name' with the actual name of your database (without the .db extension)
    db_name = "where's my RC001?"
    read_database(db_name)
