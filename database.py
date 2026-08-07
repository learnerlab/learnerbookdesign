"""Database layer — uses Supabase (PostgreSQL) when DATABASE_URL is set,
falls back to SQLite for local development."""
import os
import secrets
import time
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")

# Existing swipes with no user_id are assigned to this profile on first boot
# after the multi-user migration (preserves the original single-user history).
DEFAULT_PROFILE_NAME = os.environ.get("DEFAULT_PROFILE_NAME", "Trev")


def _new_token():
    return secrets.token_urlsafe(16)


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

    def _fetchone_dict(cur):
        row = cur.fetchone()
        if not row:
            return None
        cols = [desc[0] for desc in cur.description]
        return dict(zip(cols, row))

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
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    token TEXT NOT NULL UNIQUE,
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
            cur.execute("ALTER TABLE swipes ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_swipes_cover ON swipes(cover_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_swipes_action ON swipes(action)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_swipes_user ON swipes(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_covers_designer ON covers(designer)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_covers_genre ON covers(genre)")

            # Migrate pre-multi-user swipes to the default profile
            cur.execute("SELECT COUNT(*) FROM swipes WHERE user_id IS NULL")
            orphans = _fetchone_val(cur)
            if orphans:
                cur.execute("SELECT id FROM users WHERE name = %s", (DEFAULT_PROFILE_NAME,))
                row = cur.fetchone()
                if row:
                    default_id = row[0]
                else:
                    cur.execute(
                        "INSERT INTO users (name, token) VALUES (%s, %s) RETURNING id",
                        (DEFAULT_PROFILE_NAME, _new_token())
                    )
                    default_id = cur.fetchone()[0]
                cur.execute("UPDATE swipes SET user_id = %s WHERE user_id IS NULL", (default_id,))
                print(f"Migrated {orphans} existing swipes to profile '{DEFAULT_PROFILE_NAME}'")

    # --- Users ---

    def create_user(name):
        """Create a profile. Returns the user dict, or None if the name is taken."""
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s)", (name,))
            if cur.fetchone():
                return None
            cur.execute(
                "INSERT INTO users (name, token) VALUES (%s, %s) RETURNING id, name, token",
                (name, _new_token())
            )
            return _fetchone_dict(cur)

    def get_user_by_token(token):
        if not token:
            return None
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, token FROM users WHERE token = %s", (token,))
            return _fetchone_dict(cur)

    def get_user_by_id(user_id):
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, token FROM users WHERE id = %s", (user_id,))
            return _fetchone_dict(cur)

    def list_users():
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.id, u.name, COUNT(s.id) AS swipe_count
                FROM users u
                LEFT JOIN swipes s ON s.user_id = u.id
                GROUP BY u.id, u.name
                ORDER BY u.created_at
            """)
            return _fetchall_dicts(cur)

    # --- Covers ---

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

    def get_unswiped_covers(user_id, limit=20):
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.* FROM covers c
                LEFT JOIN swipes s ON c.id = s.cover_id AND s.user_id = %s
                WHERE s.id IS NULL
                ORDER BY RANDOM()
                LIMIT %s
            """, (user_id, limit))
            return _fetchall_dicts(cur)

    def record_swipe(cover_id, action, user_id):
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO swipes (cover_id, action, user_id) VALUES (%s, %s, %s)",
                (cover_id, action, user_id)
            )

    def get_liked_covers(user_id):
        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.*, s.action, s.swiped_at
                FROM covers c
                JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND s.user_id = %s
                ORDER BY s.swiped_at DESC
            """, (user_id,))
            return _fetchall_dicts(cur)

    def get_analytics(user_id):
        with get_db_context() as conn:
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM swipes WHERE user_id = %s", (user_id,))
            total_swiped = _fetchone_val(cur)

            cur.execute(
                "SELECT COUNT(*) FROM swipes WHERE action IN ('like', 'superlike') AND user_id = %s",
                (user_id,))
            total_likes = _fetchone_val(cur)

            cur.execute(
                "SELECT COUNT(*) FROM swipes WHERE action = 'dislike' AND user_id = %s",
                (user_id,))
            total_dislikes = _fetchone_val(cur)

            cur.execute("""
                SELECT COUNT(*) FROM covers c
                LEFT JOIN swipes s ON c.id = s.cover_id AND s.user_id = %s
                WHERE s.id IS NULL
            """, (user_id,))
            total_unswiped = _fetchone_val(cur)

            cur.execute("""
                SELECT c.designer, COUNT(*) as like_count
                FROM covers c
                JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND s.user_id = %s
                  AND c.designer IS NOT NULL AND c.designer != ''
                GROUP BY c.designer
                ORDER BY like_count DESC
                LIMIT 20
            """, (user_id,))
            top_designers = _fetchall_dicts(cur)

            cur.execute("""
                SELECT c.genre, COUNT(*) as like_count
                FROM covers c
                JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND s.user_id = %s
                  AND c.genre IS NOT NULL AND c.genre != ''
                GROUP BY c.genre
                ORDER BY like_count DESC
                LIMIT 15
            """, (user_id,))
            top_genres = _fetchall_dicts(cur)

            cur.execute("""
                SELECT c.*, s.action, s.swiped_at
                FROM covers c
                JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND s.user_id = %s
                ORDER BY s.swiped_at DESC
                LIMIT 20
            """, (user_id,))
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
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    token TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            cols = [r[1] for r in conn.execute("PRAGMA table_info(swipes)").fetchall()]
            if "user_id" not in cols:
                conn.execute("ALTER TABLE swipes ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_swipes_user ON swipes(user_id)")

            # Migrate pre-multi-user swipes to the default profile
            orphans = conn.execute(
                "SELECT COUNT(*) FROM swipes WHERE user_id IS NULL").fetchone()[0]
            if orphans:
                row = conn.execute(
                    "SELECT id FROM users WHERE name = ?", (DEFAULT_PROFILE_NAME,)).fetchone()
                if row:
                    default_id = row[0]
                else:
                    conn.execute(
                        "INSERT INTO users (name, token) VALUES (?, ?)",
                        (DEFAULT_PROFILE_NAME, _new_token()))
                    default_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute("UPDATE swipes SET user_id = ? WHERE user_id IS NULL", (default_id,))
                print(f"Migrated {orphans} existing swipes to profile '{DEFAULT_PROFILE_NAME}'")

    # --- Users ---

    def create_user(name):
        """Create a profile. Returns the user dict, or None if the name is taken."""
        with get_db_context() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE LOWER(name) = LOWER(?)", (name,)).fetchone()
            if existing:
                return None
            conn.execute(
                "INSERT INTO users (name, token) VALUES (?, ?)",
                (name, _new_token()))
            row = conn.execute(
                "SELECT id, name, token FROM users WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

    def get_user_by_token(token):
        if not token:
            return None
        with get_db_context() as conn:
            row = conn.execute(
                "SELECT id, name, token FROM users WHERE token = ?", (token,)).fetchone()
            return dict(row) if row else None

    def get_user_by_id(user_id):
        with get_db_context() as conn:
            row = conn.execute(
                "SELECT id, name, token FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def list_users():
        with get_db_context() as conn:
            rows = conn.execute("""
                SELECT u.id, u.name, COUNT(s.id) AS swipe_count
                FROM users u
                LEFT JOIN swipes s ON s.user_id = u.id
                GROUP BY u.id, u.name
                ORDER BY u.created_at
            """).fetchall()
            return [dict(r) for r in rows]

    # --- Covers ---

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

    def get_unswiped_covers(user_id, limit=20):
        with get_db_context() as conn:
            rows = conn.execute("""
                SELECT c.* FROM covers c
                LEFT JOIN swipes s ON c.id = s.cover_id AND s.user_id = ?
                WHERE s.id IS NULL
                ORDER BY RANDOM()
                LIMIT ?
            """, (user_id, limit)).fetchall()
            return [dict(r) for r in rows]

    def record_swipe(cover_id, action, user_id):
        with get_db_context() as conn:
            conn.execute(
                "INSERT INTO swipes (cover_id, action, user_id) VALUES (?, ?, ?)",
                (cover_id, action, user_id)
            )

    def get_liked_covers(user_id):
        with get_db_context() as conn:
            rows = conn.execute("""
                SELECT c.*, s.action, s.swiped_at
                FROM covers c
                JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND s.user_id = ?
                ORDER BY s.swiped_at DESC
            """, (user_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_analytics(user_id):
        with get_db_context() as conn:
            total_swiped = conn.execute(
                "SELECT COUNT(*) FROM swipes WHERE user_id = ?", (user_id,)).fetchone()[0]
            total_likes = conn.execute(
                "SELECT COUNT(*) FROM swipes WHERE action IN ('like', 'superlike') AND user_id = ?",
                (user_id,)).fetchone()[0]
            total_dislikes = conn.execute(
                "SELECT COUNT(*) FROM swipes WHERE action = 'dislike' AND user_id = ?",
                (user_id,)).fetchone()[0]
            total_unswiped = conn.execute("""
                SELECT COUNT(*) FROM covers c
                LEFT JOIN swipes s ON c.id = s.cover_id AND s.user_id = ?
                WHERE s.id IS NULL
            """, (user_id,)).fetchone()[0]
            top_designers = conn.execute("""
                SELECT c.designer, COUNT(*) as like_count
                FROM covers c JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND s.user_id = ?
                  AND c.designer IS NOT NULL AND c.designer != ''
                GROUP BY c.designer ORDER BY like_count DESC LIMIT 20
            """, (user_id,)).fetchall()
            top_genres = conn.execute("""
                SELECT c.genre, COUNT(*) as like_count
                FROM covers c JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND s.user_id = ?
                  AND c.genre IS NOT NULL AND c.genre != ''
                GROUP BY c.genre ORDER BY like_count DESC LIMIT 15
            """, (user_id,)).fetchall()
            recent_likes = conn.execute("""
                SELECT c.*, s.action, s.swiped_at
                FROM covers c JOIN swipes s ON c.id = s.cover_id
                WHERE s.action IN ('like', 'superlike') AND s.user_id = ?
                ORDER BY s.swiped_at DESC LIMIT 20
            """, (user_id,)).fetchall()
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
