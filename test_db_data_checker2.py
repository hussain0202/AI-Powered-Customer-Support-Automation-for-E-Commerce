import sqlite3
import os

# Define the path to the SQLite database
db_path = os.path.join('database', 'support.db')
print(db_path)

# Function to connect to the SQLite database
def connect_to_db():
    try:
        # Connect to the SQLite database (existing database)
        connection = sqlite3.connect(db_path)
        print("Connection to the database established successfully.")
        return connection
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

# Function to get all table names in the database
def get_all_table_names():
    try:
        connection = connect_to_db()
        if connection:
            cursor = connection.cursor()

            # Query to fetch the names of all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            # Extract table names from the result
            table_names = [table[0] for table in tables]
            return table_names
        if connection:
            connection.close()
    except sqlite3.Error as e:
        print(f"Error retrieving table names: {e}")
        return []

# Function to fetch all records from a selected table
def fetch_all_records_from_table(table_name):
    try:
        connection = connect_to_db()
        if connection:
            cursor = connection.cursor()

            # Define the SQL query to fetch all records from the specified table
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()

            print(f"Fetched records from table '{table_name}':")
            for row in rows:
                print(row)
        if connection:
            connection.close()
    except sqlite3.Error as e:
        print(f"Error fetching records from table '{table_name}': {e}")

# Function to prompt the user to select a table and then fetch its data
def interact_with_db():
    # Step 1: Fetch all table names
    table_names = get_all_table_names()

    if not table_names:
        print("No tables found in the database.")
        return

    # Step 2: Display the list of tables
    print("Available tables in the database:")
    for idx, table in enumerate(table_names, start=1):
        print(f"{idx}. {table}")

    # Step 3: Ask the user to select a table
    try:
        choice = int(input(f"Enter the number of the table you want to view (1-{len(table_names)}): "))
        if choice < 1 or choice > len(table_names):
            print("Invalid choice.")
            return
        selected_table = table_names[choice - 1]
        print(f"You selected the '{selected_table}' table.")

        # Step 4: Fetch and display data from the selected table
        fetch_all_records_from_table(selected_table)

    except ValueError:
        print("Please enter a valid number.")

# Example usage
if __name__ == "__main__":
    interact_with_db()