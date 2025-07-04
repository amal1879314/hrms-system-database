import psycopg2
from config import config
from prettytable import from_db_cursor

def connect():
    params = config()
    print("Connecting with params:", params)
    conn = psycopg2.connect(**params)
    print("Connection established!")
    return conn

def interactive_session(conn):
    try:
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print("PostgreSQL version:", cur.fetchone()[0])

        while True:
            cmd = input("\nSQL> ").strip()
            if not cmd:
                continue
            if cmd.lower() in ('exit', 'quit'):
                print("Exiting interactive session.")
                break

            try:
                cur.execute(cmd)
                if cur.description:
                    table = from_db_cursor(cur)
                    print(table)
                else:
                    conn.commit()
                    print(f"Query OK, {cur.rowcount} rows affected.")
            except Exception as e:
                print("Error executing command:", e)
                conn.rollback()

    finally:
        cur.close()
        print("Cursor closed")

def main():
    conn = None
    try:
        conn = connect()
        interactive_session(conn)
    except Exception as e:
        print("Error occurred:", e)
    finally:
        if conn:
            conn.close()
            print("Connection terminated")

if __name__ == '__main__':
    main()
