"""Database layer — uses Supabase (PostgreSQL) when DATABASE_URL is set,
falls back to SQLite for local development."""
import os
import time
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras

    def get_db():
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        conn.autocommit = False
        return conn

    @contextmanager
    def get_db_context():
        conn = get_db()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _fetchone_val(cur):
        row = cur.fetchone()
        return row[0] if row else 0

    def _fetchall_dicts(cur):
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def init_db():
        for attempt in range(4):
            try:
                _init_db_tables()
                return
            except psycopg2.OperationalError as e:
                if attempt < 3:
                    wait = 2 ** (attempt + 1)
                    print(f"DB connection failed (attempt {attempt + 1}/4), retrying in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise

    def _init_db_tables():
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS covers (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT,
                    designer TEXT,
                    genre TEXT,
                    image_url TEXT NOT NULL UNIQUE,
                    source TEXT,
                    source_url TEXT,
                    year TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS swipes (
                    id SERIAL PRIMARY KEY,
                    cover_id INTEGER NOT NULL REFERENCES covers(id),
                    action TEXT NOT NULL CHECK(action IN ('like', 'dislike', 'superlike')),
                    swiped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_swipes_cover ON swipes(cover_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_swipes_action ON swipes(action)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_covers_designer ON covers(designer)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_covers_genre ON covers(genre)")

    def get_cover_count():
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM covers")
            return _fetchone_val(cur)

    def add_cover(title, author=None, designer=None, genre=None,
                  image_url="", source=None, source_url=None, year=None):
        with get_db_context() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """INSERT INTO covers (title, author, designer, genre, image_url, source, source_url, year)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    (title, author, designer, genre, image_url, source, source_url, year)
                )
                row = cur.fetchone()
                return row[0] if row else None
            except psycopg2.IntegrityError:
                conn.rollback()
                return None

    def upsert_cover(title, author=None, designer=None, genre=None,
                     image_url="", source=None, source_url=None, year=None):
        """Insert a new cover, or update an existing one (matched by image_url).
        Only overwrites fields where the new value is non-empty."""
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO covers (title, author, designer, genre, image_url, source, source_url, year)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (image_url) DO UPDATE SET
                    title = COALESCE(NULLIF(EXCLUDED.title, ''), covers.title),
                    author = COALESCE(NULLIF(EXCLUDED.author, ''), covers.author),
                    designer = COALESCE(NULLIF(EXCLUDED.designer, ''), covers.designer),
                    genre = COALESCE(NULLIF(EXCLUDED.genre, ''), covers.genre),
                    source = COALESCE(NULLIF(EXCLUDED.source, ''), covers.source),
                    source_url = COALESCE(NULLIF(EXCLUDED.source_url, ''), covers.source_url),
                    year = COALESCE(NULLIF(EXCLUDED.year, ''), covers.year)
                RETURNING id
            """, (title, author, designer, genre, image_url, source, source_url, year))
            row = cur.fetchone()
            return row[0] if row else None

    def get_unswiped_covers(limit=20):
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.* FROM covers c
                LEFT JOIN swipes s ON c.id = s.cover_id
                WHERE s.id IS NULL
                ORDER BY RANDOM()
                LIMIT %s
            """, (limit,))
            return _fetchall_dicts(cur)

    def record_swipe(cover_id, action):
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO swipes (cover_id, action) VALUES (%s, %s)",
                (cover_id, action)
            )

    def get_liked_covers():
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.*, s.action, s.swiped_at
                FROM covers c
                JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike')
                ORDER BY s.swiped_at DESC
            """)
            return _fetchall_dicts(cur)

    def get_analytics():
        with get_db_context() as conn:
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM swipes")
            total_swiped = _fetchone_val(cur)

            cur.execute("SELECT COUNT(*) FROM swipes WHERE action IN ('like', 'superlike')")
            total_likes = _fetchone_val(cur)

            cur.execute("SELECT COUNT(*) FROM swipes WHERE action = 'dislike'")
            total_dislikes = _fetchone_val(cur)

            cur.execute("""
                SELECT COUNT(*) FROM covers c
                LEFT JOIN swipes s ON c.id = s.cover_id
                WHERE s.id IS NULL
            """)
            total_unswiped = _fetchone_val(cur)

            cur.execute("""
                SELECT c.designer, COUNT(*) as like_count
                FROM covers c
                JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND c.designer IS NOT NULL AND c.designer != ''
                GROUP BY c.designer
                ORDER BY like_count DESC
                LIMIT 20
            """)
            top_designers = _fetchall_dicts(cur)

            cur.execute("""
                SELECT c.genre, COUNT(*) as like_count
                FROM covers c
                JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND c.genre IS NOT NULL AND c.genre != ''
                GROUP BY c.genre
                ORDER BY like_count DESC
                LIMIT 15
            """)
            top_genres = _fetchall_dicts(cur)

            cur.execute("""
                SELECT c.*, s.action, s.swiped_at
                FROM covers c
                JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike')
                ORDER BY s.swiped_at DESC
                LIMIT 20
            """)
            recent_likes = _fetchall_dicts(cur)

            return {
                "total_swiped": total_swiped,
                "total_likes": total_likes,
                "total_dislikes": total_dislikes,
                "total_unswiped": total_unswiped,
                "like_rate": round(total_likes / total_swiped * 100, 1) if total_swiped > 0 else 0,
                "top_designers": top_designers,
                "top_genres": top_genres,
                "recent_likes": recent_likes,
            }

    def update_cover_designer(cover_id, designer):
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE covers SET designer = %s WHERE id = %s",
                (designer.strip(), cover_id)
            )
            return cur.rowcount > 0

    def wipe_all_data():
        """Delete ALL swipes and ALL covers. Returns (swipes_deleted, covers_deleted)."""
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM swipes")
            swipes_deleted = cur.rowcount
            cur.execute("DELETE FROM covers")
            covers_deleted = cur.rowcount
            return swipes_deleted, covers_deleted

else:
    # SQLite fallback for local development
    import sqlite3

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

    def upsert_cover(title, author=None, designer=None, genre=None,
                     image_url="", source=None, source_url=None, year=None):
        """Insert a new cover, or update an existing one (matched by image_url).
        Only overwrites fields where the new value is non-empty."""
        with get_db_context() as conn:
            conn.execute("""
                INSERT INTO covers (title, author, designer, genre, image_url, source, source_url, year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(image_url) DO UPDATE SET
                    title = COALESCE(NULLIF(excluded.title, ''), title),
                    author = COALESCE(NULLIF(excluded.author, ''), author),
                    designer = COALESCE(NULLIF(excluded.designer, ''), designer),
                    genre = COALESCE(NULLIF(excluded.genre, ''), genre),
                    source = COALESCE(NULLIF(excluded.source, ''), source),
                    source_url = COALESCE(NULLIF(excluded.source_url, ''), source_url),
                    year = COALESCE(NULLIF(excluded.year, ''), year)
            """, (title, author, designer, genre, image_url, source, source_url, year))
            row = conn.execute("SELECT id FROM covers WHERE image_url = ?", (image_url,)).fetchone()
            return row[0] if row else None

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
                FROM covers c JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND c.designer IS NOT NULL AND c.designer != ''
                GROUP BY c.designer ORDER BY like_count DESC LIMIT 20
            """).fetchall()
            top_genres = conn.execute("""
                SELECT c.genre, COUNT(*) as like_count
                FROM covers c JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND c.genre IS NOT NULL AND c.genre != ''
                GROUP BY c.genre ORDER BY like_count DESC LIMIT 15
            """).fetchall()
            recent_likes = conn.execute("""
                SELECT c.*, s.action, s.swiped_at
                FROM covers c JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike')
                ORDER BY s.swiped_at DESC LIMIT 20
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

    def update_cover_designer(cover_id, designer):
        with get_db_context() as conn:
            conn.execute(
                "UPDATE covers SET designer = ? WHERE id = ?",
                (designer.strip(), cover_id)
            )
            return True

    def wipe_all_data():
        """Delete ALL swipes and ALL covers. Returns (swipes_deleted, covers_deleted)."""
        with get_db_context() as conn:
            sc = conn.execute("SELECT COUNT(*) FROM swipes").fetchone()[0]
            cc = conn.execute("SELECT COUNT(*) FROM covers").fetchone()[0]
            conn.execute("DELETE FROM swipes")
            conn.execute("DELETE FROM covers")
            return sc, cc
