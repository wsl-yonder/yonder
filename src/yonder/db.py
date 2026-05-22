import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

from .models import FeedItem, ProcessedItem, Source


SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  url TEXT NOT NULL,
  type TEXT NOT NULL,
  channel TEXT NOT NULL,
  credibility_score REAL NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  published_at TEXT,
  raw_summary TEXT NOT NULL DEFAULT '',
  content_hash TEXT NOT NULL UNIQUE,
  channel TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE INDEX IF NOT EXISTS idx_articles_channel_created
ON articles(channel, created_at);

CREATE TABLE IF NOT EXISTS processed_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id INTEGER NOT NULL UNIQUE,
  one_liner TEXT NOT NULL,
  bullet_points TEXT NOT NULL,
  importance TEXT NOT NULL,
  uncertainty TEXT NOT NULL,
  score REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE TABLE IF NOT EXISTS digests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  content_markdown TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sent_at TEXT
);

CREATE TABLE IF NOT EXISTS push_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  digest_id INTEGER,
  target TEXT NOT NULL,
  success INTEGER NOT NULL,
  response TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (digest_id) REFERENCES digests(id)
);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(database_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_sources(conn: sqlite3.Connection, sources: Iterable[Source]) -> None:
    for source in sources:
        conn.execute(
            """
            INSERT INTO sources (name, url, type, channel, credibility_score, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
              url = excluded.url,
              type = excluded.type,
              channel = excluded.channel,
              credibility_score = excluded.credibility_score,
              enabled = excluded.enabled,
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                source.name,
                source.url,
                source.type,
                source.channel,
                source.credibility_score,
                1 if source.enabled else 0,
            ),
        )
    conn.commit()


def source_id_by_name(conn: sqlite3.Connection, name: str) -> Optional[int]:
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()
    return int(row["id"]) if row else None


def insert_article(conn: sqlite3.Connection, item: FeedItem, content_hash: str) -> bool:
    source_id = source_id_by_name(conn, item.source_name)
    if source_id is None:
        raise ValueError(f"Source is not registered: {item.source_name}")

    published_at = item.published_at.isoformat() if item.published_at else None
    try:
        conn.execute(
            """
            INSERT INTO articles (
              source_id, title, url, published_at, raw_summary, content_hash, channel
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                item.title,
                item.url,
                published_at,
                item.raw_summary,
                content_hash,
                item.channel,
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def unprocessed_articles(conn: sqlite3.Connection, limit: int = 100) -> List[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT
          articles.*,
          sources.name AS source_name,
          sources.credibility_score AS credibility_score
        FROM articles
        JOIN sources ON sources.id = articles.source_id
        LEFT JOIN processed_items ON processed_items.article_id = articles.id
        WHERE processed_items.id IS NULL
        ORDER BY COALESCE(articles.published_at, articles.created_at) DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return list(rows)


def insert_processed_item(conn: sqlite3.Connection, item: ProcessedItem) -> None:
    conn.execute(
        """
        INSERT INTO processed_items (
          article_id, one_liner, bullet_points, importance, uncertainty, score
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(article_id) DO UPDATE SET
          one_liner = excluded.one_liner,
          bullet_points = excluded.bullet_points,
          importance = excluded.importance,
          uncertainty = excluded.uncertainty,
          score = excluded.score
        """,
        (
            item.article_id,
            item.one_liner,
            item.bullet_points,
            item.importance,
            item.uncertainty,
            item.score,
        ),
    )
    conn.commit()


def top_items_by_channel(
    conn: sqlite3.Connection, channel: str, limit: int
) -> List[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT
          processed_items.*,
          articles.title,
          articles.url,
          articles.channel,
          articles.published_at,
          sources.name AS source_name
        FROM processed_items
        JOIN articles ON articles.id = processed_items.article_id
        JOIN sources ON sources.id = articles.source_id
        WHERE articles.channel = ?
        ORDER BY processed_items.score DESC, processed_items.created_at DESC
        LIMIT ?
        """,
        (channel, limit),
    ).fetchall()
    return list(rows)


def dashboard_items(
    conn: sqlite3.Connection,
    channel: Optional[str] = None,
    query: str = "",
    limit: int = 200,
) -> List[sqlite3.Row]:
    conditions = []
    params = []

    if channel:
        conditions.append("articles.channel = ?")
        params.append(channel)

    if query:
        conditions.append(
            """
            (
              articles.title LIKE ?
              OR articles.raw_summary LIKE ?
              OR sources.name LIKE ?
              OR processed_items.one_liner LIKE ?
            )
            """
        )
        needle = f"%{query}%"
        params.extend([needle, needle, needle, needle])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    rows = conn.execute(
        f"""
        SELECT
          articles.id AS article_id,
          articles.title,
          articles.url,
          articles.channel,
          articles.published_at,
          articles.created_at,
          sources.name AS source_name,
          processed_items.one_liner,
          processed_items.bullet_points,
          processed_items.importance,
          processed_items.uncertainty,
          processed_items.score
        FROM articles
        JOIN sources ON sources.id = articles.source_id
        LEFT JOIN processed_items ON processed_items.article_id = articles.id
        {where}
        ORDER BY
          COALESCE(processed_items.score, 0) DESC,
          COALESCE(articles.published_at, articles.created_at) DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return list(rows)


def dashboard_stats(conn: sqlite3.Connection) -> sqlite3.Row:
    return conn.execute(
        """
        SELECT
          COUNT(*) AS total_articles,
          SUM(CASE WHEN channel = 'ai' THEN 1 ELSE 0 END) AS ai_count,
          SUM(CASE WHEN channel = 'finance' THEN 1 ELSE 0 END) AS finance_count,
          SUM(CASE WHEN channel = 'tech' THEN 1 ELSE 0 END) AS tech_count,
          MAX(created_at) AS last_collected_at
        FROM articles
        """
    ).fetchone()


def latest_digest(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    row = conn.execute(
        """
        SELECT *
        FROM digests
        ORDER BY generated_at DESC
        LIMIT 1
        """
    ).fetchone()
    return row


def insert_digest(conn: sqlite3.Connection, title: str, content_markdown: str) -> int:
    cursor = conn.execute(
        "INSERT INTO digests (title, content_markdown) VALUES (?, ?)",
        (title, content_markdown),
    )
    conn.commit()
    return int(cursor.lastrowid)


def mark_digest_sent(conn: sqlite3.Connection, digest_id: int) -> None:
    conn.execute(
        "UPDATE digests SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE id = ?",
        (digest_id,),
    )
    conn.commit()


def insert_push_history(
    conn: sqlite3.Connection, digest_id: Optional[int], target: str, success: bool, response: str
) -> None:
    conn.execute(
        """
        INSERT INTO push_history (digest_id, target, success, response)
        VALUES (?, ?, ?, ?)
        """,
        (digest_id, target, 1 if success else 0, response),
    )
    conn.commit()
