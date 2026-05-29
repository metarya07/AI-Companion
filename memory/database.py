import sqlite3

DB_NAME = "jarvis.db"


def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_memory(memory_text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO memories (memory_text) VALUES (?)",
        (memory_text,)
    )

    conn.commit()
    conn.close()


def get_memories():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, memory_text FROM memories"
    )

    memories = cursor.fetchall()

    conn.close()

    return memories


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
