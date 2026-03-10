import sqlite3
import os 
from datetime import datetime

DB_NAME = "support_tickets.db"

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the tickets table."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL);""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL, category TEXT,user_id TEXT, priority TEXT, ai_resolution TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(username));""")
        conn.commit()
    finally:
        conn.close()

def create_user(username, password_hash, role = "user"):
    """Create a new user in the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO users (username, password_hash, role)VALUES (?, ?, ?)""", (username, password_hash, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # User already exists
    finally:
        conn.close()

def get_user(username):
    """Retrieves a user by username."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()
    finally:
        conn.close()

if __name__ =="__main__":
    init_db()
    print(f"Database {DB_NAME}  initialized successfully.")


      
