import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "bookcovers.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db_context():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db_context() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS covers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT,
                designer TEXT,
                genre TEXT,
                image_url TEXT NOT NULL,
                source TEXT,
                source_url TEXT,
                year TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(image_url)
            );

            CREATE TABLE IF NOT EXISTS swipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cover_id INTEGER NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('like', 'dislike', 'superlike')),
                swiped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cover_id) REFERENCES covers(id)
            );

            CREATE TABLE IF NOT EXISTS designers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                website TEXT,
                email TEXT,
                notes TEXT,
                contacted INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_swipes_cover ON swipes(cover_id);
            CREATE INDEX IF NOT EXISTS idx_swipes_action ON swipes(action);
            CREATE INDEX IF NOT EXISTS idx_covers_designer ON covers(designer);
            CREATE INDEX IF NOT EXISTS idx_covers_genre ON covers(genre);
        """)


def get_cover_count():
    with get_db_context() as conn:
        return conn.execute("SELECT COUNT(*) FROM covers").fetchone()[0]


def add_cover(title, author=None, designer=None, genre=None,
              image_url="", source=None, source_url=None, year=None):
    with get_db_context() as conn:
        try:
            conn.execute(
                """INSERT INTO covers (title, author, designer, genre, image_url, source, source_url, year)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, author, designer, genre, image_url, source, source_url, year)
            )
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return None


def get_unswiped_covers(limit=20):
    with get_db_context() as conn:
        rows = conn.execute("""
            SELECT c.* FROM covers c
            LEFT JOIN swipes s ON c.id = s.cover_id
            WHERE s.id IS NULL
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def record_swipe(cover_id, action):
    with get_db_context() as conn:
        conn.execute(
            "INSERT INTO swipes (cover_id, action) VALUES (?, ?)",
            (cover_id, action)
        )


def get_liked_covers():
    with get_db_context() as conn:
        rows = conn.execute("""
            SELECT c.*, s.action, s.swiped_at
            FROM covers c
            JOIN swipes s ON c.id = s.cover_id
            WHERE s.action IN ('like', 'superlike')
            ORDER BY s.swiped_at DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_analytics():
    with get_db_context() as conn:
        total_swiped = conn.execute("SELECT COUNT(*) FROM swipes").fetchone()[0]
        total_likes = conn.execute(
            "SELECT COUNT(*) FROM swipes WHERE action IN ('like', 'superlike')"
        ).fetchone()[0]
        total_dislikes = conn.execute(
            "SELECT COUNT(*) FROM swipes WHERE action = 'dislike'"
        ).fetchone()[0]
        total_unswiped = conn.execute("""
            SELECT COUNT(*) FROM covers c
            LEFT JOIN swipes s ON c.id = s.cover_id
            WHERE s.id IS NULL
        """).fetchone()[0]

        top_designers = conn.execute("""
            SELECT c.designer, COUNT(*) as like_count
            FROM covers c
            JOIN swipes s ON c.id = s.cover_id
            WHERE s.action IN ('like', 'superlike') AND c.designer IS NOT NULL AND c.designer != ''
            GROUP BY c.designer
            ORDER BY like_count DESC
            LIMIT 20
        """).fetchall()

        top_genres = conn.execute("""
            SELECT c.genre, COUNT(*) as like_count
            FROM covers c
            JOIN swipes s ON c.id = s.cover_id
            WHERE s.action IN ('like', 'superlike') AND c.genre IS NOT NULL AND c.genre != ''
            GROUP BY c.genre
            ORDER BY like_count DESC
            LIMIT 15
        """).fetchall()

        recent_likes = conn.execute("""
            SELECT c.*, s.action, s.swiped_at
            FROM covers c
            JOIN swipes s ON c.id = s.cover_id
            WHERE s.action IN ('like', 'superlike')
            ORDER BY s.swiped_at DESC
            LIMIT 20
        """).fetchall()

        return {
            "total_swiped": total_swiped,
            "total_likes": total_likes,
            "total_dislikes": total_dislikes,
            "total_unswiped": total_unswiped,
            "like_rate": round(total_likes / total_swiped * 100, 1) if total_swiped > 0 else 0,
            "top_designers": [dict(r) for r in top_designers],
            "top_genres": [dict(r) for r in top_genres],
            "recent_likes": [dict(r) for r in recent_likes],
        }
