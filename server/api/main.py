"""
API — serves arc data and analytics to the frontend.

Endpoints:
    GET  /api/books                          paginated book catalog
    GET  /api/books/{book_id}                book metadata
    GET  /api/books/{book_id}/arc            full arc data (all chunks)
    GET  /api/books/{book_id}/characters     character presence data
    GET  /api/compare?ids=1,2,3              arc data for multiple books overlaid
    GET  /api/explore/genres                 average tension curves by genre

Usage:
    uvicorn main:app --reload --port 8000
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery

load_dotenv()

BQ_PROJECT = os.getenv("GCP_PROJECT_ID")
BQ_DATASET = os.getenv("BQ_DATASET", "overdue")

app = FastAPI(title="Overdue API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

bq = bigquery.Client(project=BQ_PROJECT)


def run(sql: str) -> list[dict]:
    return [dict(row) for row in bq.query(sql).result()]


# ----------------------------------------------------------------------
# Books
# ----------------------------------------------------------------------

@app.get("/api/books")
def list_books(
    limit: int = 50,
    offset: int = 0,
    author: str = None,
    language: str = None,
):
    filters = ["processed_at IS NOT NULL"]
    if author:
        filters.append(f"LOWER(author) LIKE LOWER('%{author}%')")
    if language:
        filters.append(f"language = '{language}'")

    where = "WHERE " + " AND ".join(filters)

    return run(f"""
        SELECT book_id, title, author, subjects, language, publish_year, word_count
        FROM `{BQ_PROJECT}.{BQ_DATASET}.books`
        {where}
        ORDER BY title
        LIMIT {limit} OFFSET {offset}
    """)


@app.get("/api/books/{book_id}")
def get_book(book_id: str):
    rows = run(f"""
        SELECT *
        FROM `{BQ_PROJECT}.{BQ_DATASET}.books`
        WHERE book_id = '{book_id}'
        LIMIT 1
    """)
    if not rows:
        raise HTTPException(status_code=404, detail="Book not found")
    return rows[0]


# ----------------------------------------------------------------------
# Arc data
# ----------------------------------------------------------------------

@app.get("/api/books/{book_id}/arc")
def get_arc(book_id: str):
    return run(f"""
        SELECT
            chunk_index,
            position_pct,
            chapter,
            word_count,
            sentiment_score,
            tension_score,
            pacing_score,
            conflict_density,
            dominant_characters
        FROM `{BQ_PROJECT}.{BQ_DATASET}.book_arcs`
        WHERE book_id = '{book_id}'
        ORDER BY chunk_index
    """)


@app.get("/api/books/{book_id}/characters")
def get_characters(book_id: str):
    return run(f"""
        SELECT
            character_name,
            mention_count,
            first_appearance_pct,
            last_appearance_pct,
            peak_presence_pct
        FROM `{BQ_PROJECT}.{BQ_DATASET}.characters`
        WHERE book_id = '{book_id}'
        ORDER BY mention_count DESC
    """)


# ----------------------------------------------------------------------
# Compare
# ----------------------------------------------------------------------

@app.get("/api/compare")
def compare_books(ids: str = Query(..., description="Comma-separated book IDs")):
    book_ids = [i.strip() for i in ids.split(",")]
    id_list = ", ".join(f"'{i}'" for i in book_ids)

    rows = run(f"""
        SELECT book_id, chunk_index, position_pct, tension_score, sentiment_score, pacing_score
        FROM `{BQ_PROJECT}.{BQ_DATASET}.book_arcs`
        WHERE book_id IN ({id_list})
        ORDER BY book_id, chunk_index
    """)

    # Group by book_id so the frontend gets { "84": [...], "1342": [...] }
    result: dict = {}
    for row in rows:
        result.setdefault(row["book_id"], []).append(row)
    return result


# ----------------------------------------------------------------------
# Explore
# ----------------------------------------------------------------------

@app.get("/api/explore/genres")
def genre_tension():
    return run(f"""
        SELECT
            subject,
            ROUND(AVG(a.tension_score), 4)   AS avg_tension,
            ROUND(AVG(a.sentiment_score), 4) AS avg_sentiment,
            ROUND(AVG(a.pacing_score), 4)    AS avg_pacing,
            COUNT(DISTINCT a.book_id)        AS book_count
        FROM `{BQ_PROJECT}.{BQ_DATASET}.book_arcs` a
        JOIN `{BQ_PROJECT}.{BQ_DATASET}.books` b USING (book_id)
        CROSS JOIN UNNEST(b.subjects) AS subject
        GROUP BY subject
        HAVING book_count >= 3
        ORDER BY avg_tension DESC
        LIMIT 20
    """)
