"""
Legal Chunks → pgvector Ingestion Pipeline
==========================================
- Embeds chunks using BAAI/bge-m3 (1024-dim)
- Stores in local PostgreSQL with pgvector
- Builds hybrid search: semantic (pgvector) + keyword (tsvector)
- Idempotent: safe to re-run, skips already-ingested chunks

Usage:
    # Setup DB schema (first time only)
    python ingest.py --setup

    # Ingest chunks
    python ingest.py --input chunks.json

    # Test hybrid search
    python ingest.py --search "jurisdiction of district commission"
    python ingest.py --search "section 35" --mode keyword
    python ingest.py --search "consumer rights defective product" --mode hybrid

ENV (set in .env or export):
    DATABASE_URL=postgresql://user:pass@localhost:5432/legalease
"""

import os
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras
from sentence_transformers import SentenceTransformer

# ── Optional: load .env ───────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/legalease"
)

EMBED_MODEL = "BAAI/bge-m3"
EMBED_DIM = 1024
BATCH_SIZE = 4           # BGE-M3 is heavy — 4 is safe on M-series / CPU
TABLE_NAME = "legal_chunks"


# ─────────────────────────────────────────────
# DB SCHEMA
# ─────────────────────────────────────────────

SCHEMA_SQL = f"""
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main legal chunks table
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id              TEXT PRIMARY KEY,
    text            TEXT NOT NULL,
    chunk_type      TEXT,                    -- preamble | section | definition | schedule
    parent_id       TEXT,                    -- child chunks reference their parent section

    -- Legal location
    act_name        TEXT,
    act_year        INTEGER,
    law_type        TEXT,                    -- consumer_protection | labour_law | etc.
    chapter_num     TEXT,
    chapter_title   TEXT,
    section_num     TEXT,
    section_title   TEXT,

    -- Content flags (useful for filtered retrieval)
    has_proviso            BOOLEAN DEFAULT FALSE,
    has_explanation        BOOLEAN DEFAULT FALSE,
    is_definition_section  BOOLEAN DEFAULT FALSE,
    cross_refs             TEXT[],           -- array of referenced sections

    -- Source
    source_file     TEXT,
    page_range      INTEGER[],
    chunk_index     INTEGER,
    word_count      INTEGER,

    -- Search columns
    embedding       vector({EMBED_DIM}),     -- BGE-M3 semantic vector
    fts             tsvector,               -- full-text search index

    -- Audit
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ──────────────────────────────────────────────────────────────────

-- Semantic search: cosine similarity (HNSW for fast ANN)
CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_embedding
    ON {TABLE_NAME} USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search
CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_fts
    ON {TABLE_NAME} USING gin (fts);

-- Metadata filters (used in WHERE clauses alongside vector search)
CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_law_type   ON {TABLE_NAME} (law_type);
CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_act_name   ON {TABLE_NAME} (act_name);
CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_section    ON {TABLE_NAME} (section_num);
CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_chunk_type ON {TABLE_NAME} (chunk_type);
CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_parent_id  ON {TABLE_NAME} (parent_id);

-- Trigger: auto-update fts column on insert/update
CREATE OR REPLACE FUNCTION update_legal_fts() RETURNS trigger AS $$
BEGIN
    NEW.fts := to_tsvector('english',
        coalesce(NEW.act_name, '')    || ' ' ||
        coalesce(NEW.section_title, '') || ' ' ||
        coalesce(NEW.chapter_title, '') || ' ' ||
        coalesce(NEW.text, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_legal_fts ON {TABLE_NAME};
CREATE TRIGGER trg_legal_fts
    BEFORE INSERT OR UPDATE ON {TABLE_NAME}
    FOR EACH ROW EXECUTE FUNCTION update_legal_fts();
"""


# ─────────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(DATABASE_URL)


def setup_schema():
    log.info("Setting up database schema...")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()
    log.info("✓ Schema ready")


# ─────────────────────────────────────────────
# EMBEDDINGS
# ─────────────────────────────────────────────

_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        log.info(f"Loading {EMBED_MODEL} (first run downloads ~2GB)...")

        # BGE-M3 is too large for MPS (Apple Silicon GPU) — it OOMs at batch inference.
        # CPU is slower but stable. On a machine with a proper NVIDIA GPU, change to "cuda".
        import torch
        if torch.backends.mps.is_available():
            device = "cpu"
            log.info(
                "  → MPS detected but forcing CPU (BGE-M3 too large for MPS batch inference)")
        elif torch.cuda.is_available():
            device = "cuda"
            log.info("  → Using CUDA GPU")
        else:
            device = "cpu"
            log.info("  → Using CPU")

        _model = SentenceTransformer(EMBED_MODEL, device=device)
        log.info("✓ Model loaded")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embeds in small batches with progress tracking.
    BGE-M3 document side needs no instruction prefix.
    """
    model = get_model()
    all_vecs = []
    total = len(texts)

    for start in range(0, total, BATCH_SIZE):
        batch = texts[start: start + BATCH_SIZE]
        vecs = model.encode(
            batch,
            batch_size=BATCH_SIZE,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        all_vecs.extend(vecs.tolist())
        done = min(start + BATCH_SIZE, total)
        log.info(f"  Embedded {done}/{total} chunks...")

    return all_vecs


def embed_query(query: str) -> list[float]:
    """
    For queries, BGE-M3 recommends an instruction prefix for retrieval tasks.
    """
    instruction = "Represent this sentence for searching relevant passages: "
    model = get_model()
    vec = model.encode(
        instruction + query,
        normalize_embeddings=True,
        convert_to_numpy=True
    )
    return vec.tolist()


# ─────────────────────────────────────────────
# INGESTION
# ─────────────────────────────────────────────

def get_existing_ids(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(f"SELECT id FROM {TABLE_NAME}")
        return {row[0] for row in cur.fetchall()}


def ingest(chunks_file: str):
    log.info(f"Loading chunks from {chunks_file}")
    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    log.info(f"  → {len(chunks)} total chunks loaded")

    conn = get_conn()
    existing_ids = get_existing_ids(conn)
    log.info(f"  → {len(existing_ids)} already in DB (will skip)")

    # Filter to new chunks only
    new_chunks = [c for c in chunks if c["id"] not in existing_ids]
    log.info(f"  → {len(new_chunks)} new chunks to ingest")

    if not new_chunks:
        log.info("Nothing new to ingest.")
        conn.close()
        return

    # Embed in batches
    texts = [c["text"] for c in new_chunks]
    log.info(f"Embedding {len(texts)} chunks in batches of {BATCH_SIZE}...")
    t0 = time.time()
    embeddings = embed_texts(texts)
    log.info(f"  → Embedding done in {time.time()-t0:.1f}s")

    # Insert into DB
    insert_sql = f"""
        INSERT INTO {TABLE_NAME} (
            id, text, chunk_type, parent_id,
            act_name, act_year, law_type,
            chapter_num, chapter_title,
            section_num, section_title,
            has_proviso, has_explanation, is_definition_section,
            cross_refs, source_file, page_range,
            chunk_index, word_count, embedding
        ) VALUES (
            %(id)s, %(text)s, %(chunk_type)s, %(parent_id)s,
            %(act_name)s, %(act_year)s, %(law_type)s,
            %(chapter_num)s, %(chapter_title)s,
            %(section_num)s, %(section_title)s,
            %(has_proviso)s, %(has_explanation)s, %(is_definition_section)s,
            %(cross_refs)s, %(source_file)s, %(page_range)s,
            %(chunk_index)s, %(word_count)s, %(embedding)s
        )
        ON CONFLICT (id) DO NOTHING
    """

    log.info("Writing to database...")
    batch = []
    inserted = 0

    with conn.cursor() as cur:
        for chunk, vec in zip(new_chunks, embeddings):
            row = {
                "id":                   chunk["id"],
                "text":                 chunk["text"],
                "chunk_type":           chunk.get("chunk_type"),
                "parent_id":            chunk.get("parent_id"),
                "act_name":             chunk.get("act_name"),
                "act_year":             chunk.get("act_year"),
                "law_type":             chunk.get("law_type"),
                "chapter_num":          chunk.get("chapter_num"),
                "chapter_title":        chunk.get("chapter_title"),
                "section_num":          chunk.get("section_num"),
                "section_title":        chunk.get("section_title"),
                "has_proviso":          chunk.get("has_proviso", False),
                "has_explanation":      chunk.get("has_explanation", False),
                "is_definition_section": chunk.get("is_definition_section", False),
                "cross_refs":           chunk.get("cross_refs", []),
                "source_file":          chunk.get("source_file"),
                "page_range":           chunk.get("page_range", []),
                "chunk_index":          chunk.get("chunk_index"),
                "word_count":           chunk.get("word_count"),
                "embedding":            vec,
            }
            batch.append(row)

            if len(batch) >= 100:
                psycopg2.extras.execute_batch(cur, insert_sql, batch)
                conn.commit()
                inserted += len(batch)
                log.info(f"  → {inserted}/{len(new_chunks)} inserted...")
                batch = []

        # Flush remaining
        if batch:
            psycopg2.extras.execute_batch(cur, insert_sql, batch)
            conn.commit()
            inserted += len(batch)

    conn.close()
    log.info(f"✓ Ingestion complete. {inserted} chunks inserted.")


# ─────────────────────────────────────────────
# SEARCH (for testing)
# ─────────────────────────────────────────────

def search(
    query: str,
    mode: str = "hybrid",        # semantic | keyword | hybrid
    law_type: Optional[str] = None,
    top_k: int = 5
):
    """
    hybrid  = RRF fusion of semantic + keyword results
    semantic = cosine similarity on embedding
    keyword  = PostgreSQL full-text search
    """
    conn = get_conn()

    filter_clause = ""
    filter_params: dict = {}
    if law_type:
        filter_clause = "AND law_type = %(law_type)s"
        filter_params["law_type"] = law_type

    results = []

    # ── Semantic ──────────────────────────────────────────────────────────────
    if mode in ("semantic", "hybrid"):
        qvec = embed_query(query)
        sem_sql = f"""
            SELECT
                id, section_num, section_title, act_name, law_type,
                left(text, 300) AS preview,
                1 - (embedding <=> %(vec)s::vector) AS score
            FROM {TABLE_NAME}
            WHERE 1=1 {filter_clause}
            ORDER BY embedding <=> %(vec)s::vector
            LIMIT %(k)s
        """
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sem_sql, {"vec": qvec, "k": top_k, **filter_params})
            sem_results = cur.fetchall()

        if mode == "semantic":
            results = sem_results

    # ── Keyword ───────────────────────────────────────────────────────────────
    if mode in ("keyword", "hybrid"):
        kw_sql = f"""
            SELECT
                id, section_num, section_title, act_name, law_type,
                left(text, 300) AS preview,
                ts_rank(fts, plainto_tsquery('english', %(query)s)) AS score
            FROM {TABLE_NAME}
            WHERE fts @@ plainto_tsquery('english', %(query)s) {filter_clause}
            ORDER BY score DESC
            LIMIT %(k)s
        """
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(kw_sql, {"query": query, "k": top_k, **filter_params})
            kw_results = cur.fetchall()

        if mode == "keyword":
            results = kw_results

    # ── Hybrid: Reciprocal Rank Fusion ────────────────────────────────────────
    if mode == "hybrid":
        k_rrf = 60  # RRF constant
        rrf_scores: dict[str, float] = {}
        rrf_rows: dict[str, dict] = {}

        for rank, row in enumerate(sem_results):
            rid = row["id"]
            rrf_scores[rid] = rrf_scores.get(rid, 0) + 1 / (k_rrf + rank + 1)
            rrf_rows[rid] = row

        for rank, row in enumerate(kw_results):
            rid = row["id"]
            rrf_scores[rid] = rrf_scores.get(rid, 0) + 1 / (k_rrf + rank + 1)
            rrf_rows[rid] = row

        ranked = sorted(rrf_scores.items(),
                        key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for rid, score in ranked:
            r = dict(rrf_rows[rid])
            r["score"] = round(score, 4)
            results.append(r)

    conn.close()

    # ── Print results ─────────────────────────────────────────────────────────
    print(f"\n── {mode.upper()} Search: '{query}' ──────────────────────────")
    if not results:
        print("  No results found.")
        return []

    for i, r in enumerate(results):
        print(f"\n  [{i+1}] Score: {r.get('score', '?'):.4f}")
        print(f"       Act    : {r['act_name']}")
        print(f"       Section: {r['section_num']} — {r['section_title']}")
        print(f"       Type   : {r['law_type']}")
        print(f"       Preview: {r['preview'][:200]}...")
    print("─" * 60)
    return results


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Legal Chunks → pgvector Ingestion")
    parser.add_argument("--setup",  action="store_true",
                        help="Create DB schema (run once)")
    parser.add_argument(
        "--input",  "-i", default="chunks.json", help="Path to chunks.json")
    parser.add_argument("--search", "-s", type=str,
                        help="Test search query")
    parser.add_argument("--mode",   default="hybrid",
                        choices=["semantic", "keyword", "hybrid"])
    parser.add_argument("--law-type", type=str,
                        help="Filter by law type")
    parser.add_argument("--top-k",  type=int, default=5,
                        help="Number of results")
    args = parser.parse_args()

    if args.setup:
        setup_schema()

    if args.input and not args.search:
        ingest(args.input)

    if args.search:
        search(args.search, mode=args.mode,
               law_type=args.law_type, top_k=args.top_k)
