import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "data/agent.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'wishlist',
            url TEXT,
            notes TEXT,
            date_applied TEXT,
            deadline TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # status options: wishlist | applied | screening | interview | offer | rejected

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            priority TEXT DEFAULT 'medium',
            due_date TEXT,
            done INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # category: uni_exam | uni_assignment | uni_project | uni_class | job_application | job_interview | networking | general
    # priority: high | medium | low

    conn.commit()
    conn.close()


# ── Job Applications ──────────────────────────────────────────────────────────

def add_application(company: str, role: str, status: str = "applied",
                    url: str = None, notes: str = None,
                    date_applied: str = None, deadline: str = None) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications (company, role, status, url, notes, date_applied, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (company, role, status, url, notes,
          date_applied or datetime.now().strftime("%Y-%m-%d"), deadline))
    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id


def find_application(company: str, role: str) -> dict | None:
    """Return the first matching application (case-insensitive) or None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM applications WHERE LOWER(company) = LOWER(?) AND LOWER(role) = LOWER(?)",
        (company, role),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_application(app_id: int, **kwargs) -> bool:
    allowed = {"company", "role", "status", "url", "notes", "date_applied", "deadline"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    cols = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [app_id]
    conn = get_conn()
    conn.execute(f"UPDATE applications SET {cols} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return True


def list_applications(status: str = None) -> list[dict]:
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM applications WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Planner Tasks ─────────────────────────────────────────────────────────────

def add_task(title: str, category: str = "general", priority: str = "medium",
             due_date: str = None, notes: str = None) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tasks (title, category, priority, due_date, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (title, category, priority, due_date, notes))
    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id


def complete_task(task_id: int) -> bool:
    conn = get_conn()
    conn.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return True


def list_tasks(category: str = None, done: bool = False) -> list[dict]:
    conn = get_conn()
    query = "SELECT * FROM tasks WHERE done = ?"
    params = [int(done)]
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, due_date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
