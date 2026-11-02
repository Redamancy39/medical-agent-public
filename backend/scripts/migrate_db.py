import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import load_settings

settings = load_settings()
conn = sqlite3.connect(settings.database_path)
cur = conn.cursor()

cur.execute("PRAGMA table_info(memory_facts)")
cols = [r[1] for r in cur.fetchall()]
print("Current memory_facts cols:", cols)
if "entity_type" not in cols:
    cur.execute("ALTER TABLE memory_facts ADD COLUMN entity_type VARCHAR(30) DEFAULT 'self'")
    conn.commit()
    print("Added column entity_type to memory_facts!")

cur.execute("PRAGMA table_info(session_learning_states)")
cols_l = [r[1] for r in cur.fetchall()]
print("Current session_learning_states cols:", cols_l)
if not cols_l:
    cur.execute("""
    CREATE TABLE session_learning_states (
        session_id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        learning_goal VARCHAR(200) DEFAULT '心血管与慢病循证知识学习',
        completed_topics_json TEXT DEFAULT '[]',
        unresolved_questions_json TEXT DEFAULT '[]',
        next_steps_json TEXT DEFAULT '[]',
        last_topic VARCHAR(200),
        last_entities_json TEXT DEFAULT '[]',
        updated_at VARCHAR(40)
    )
    """)
    conn.commit()
    print("Created session_learning_states table!")

conn.close()
print("Migration completed successfully.")
