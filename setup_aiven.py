"""
Spend Smart — Aiven Database Initializer
Safely executes database/aiven_setup.sql against your remote Aiven MySQL database.
Passes credentials interactively via getpass without saving or printing them.
"""

import os
import getpass
import mysql.connector

def run_setup():
    print("=" * 60)
    print("   Spend Smart — Aiven MySQL Database Initializer")
    print("=" * 60)
    print("This script connects to Aiven MySQL and creates the 'expenses' table")
    print("directly inside your existing 'defaultdb' database.\n")
    
    host = input("Aiven Host (e.g. mysql-xxxx.aivencloud.com): ").strip()
    if not host:
        print("Error: Host cannot be empty.")
        return

    port_input = input("Aiven Port (e.g. 12345): ").strip()
    try:
        port = int(port_input)
    except ValueError:
        print("Error: Port must be a valid number.")
        return

    user = input("Aiven User [default: avnadmin]: ").strip() or "avnadmin"
    password = getpass.getpass("Aiven Password (input hidden): ").strip()
    if not password:
        print("Error: Password cannot be empty.")
        return

    database = input("Aiven Database [default: defaultdb]: ").strip() or "defaultdb"

    sql_path = os.path.join(os.path.dirname(__file__), "database", "aiven_setup.sql")
    if not os.path.exists(sql_path):
        print(f"Error: SQL file not found at {sql_path}")
        return

    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print("\nConnecting to Aiven MySQL using SSL encryption...")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl_disabled=False,
            ssl_verify_cert=False
        )
        cursor = conn.cursor()
        print("Connected successfully to Aiven MySQL!")

        print("Executing database/aiven_setup.sql...")
        for statement in sql_content.split(";"):
            # Strip SQL comments
            lines = [l for l in statement.splitlines() if not l.strip().startswith("--")]
            clean_stmt = "\n".join(lines).strip()
            if clean_stmt:
                cursor.execute(clean_stmt)
        conn.commit()

        # Verify the table actually exists
        cursor.execute("SHOW TABLES LIKE 'expenses'")
        table_found = cursor.fetchone()

        if table_found:
            print("\nVERIFIED: 'expenses' table successfully created in '" + database + "'!")
            cursor.execute("DESCRIBE expenses")
            print("\nTable schema verified:")
            for col in cursor.fetchall():
                print(f"  • {col[0]} ({col[1]})")
            print("\nYour Aiven database is ready for Render deployment!")
        else:
            print("\nNotice: Table creation command completed, but table was not detected.")

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"\nConnection or execution failed: {err}")
        print("Please check your Aiven Host, Port, User, and Password, and ensure your service is RUNNING.")

if __name__ == "__main__":
    run_setup()
