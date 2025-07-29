from passlib.hash import bcrypt
import psycopg2
from config import config

def rehash_all_user_passwords():
    conn = psycopg2.connect(**config())
    cur = conn.cursor()

    cur.execute("SELECT id, password FROM users")
    users = cur.fetchall()

    for user_id, password in users:
        if not password.startswith("$2b$"):  # Not hashed
            hashed_password = bcrypt.hash(password)
            cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))
            print(f"Rehashed password for user {user_id}")
        else:
            print(f"Already hashed: User {user_id}")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ All passwords processed.")

if __name__ == "__main__":
    rehash_all_user_passwords()
