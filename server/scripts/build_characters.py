"""
build_characters.py — computes per-book character presence stats from book_arcs
and writes them to the characters table.

Run this after the full pipeline has processed a batch of books.

Usage:
    python scripts/build_characters.py                  # process all books
    python scripts/build_characters.py --book-id 1342   # single book
"""

import os
import logging
import argparse
from collections import defaultdict
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BQ_PROJECT = os.getenv("GCP_PROJECT_ID")
BQ_DATASET = os.getenv("BQ_DATASET", "overdue")


def fetch_arcs(bq: bigquery.Client, book_id: str = None) -> list[dict]:
    where = f"WHERE book_id = '{book_id}'" if book_id else ""
    rows = bq.query(f"""
        SELECT book_id, chunk_index, position_pct, dominant_characters
        FROM `{BQ_PROJECT}.{BQ_DATASET}.book_arcs`
        {where}
        ORDER BY book_id, chunk_index
    """).result()
    return [dict(row) for row in rows]


def compute_characters(arcs: list[dict]) -> list[dict]:
    """
    For each book, compute per-character stats across all its chunks.
    Returns rows ready to insert into the characters table.
    """
    # Group arcs by book
    books: dict[str, list[dict]] = defaultdict(list)
    for arc in arcs:
        books[arc["book_id"]].append(arc)

    rows = []
    for book_id, chunks in books.items():
        # Track positions where each character appears
        char_positions: dict[str, list[float]] = defaultdict(list)

        for chunk in chunks:
            pos = chunk["position_pct"]
            for name in (chunk["dominant_characters"] or []):
                char_positions[name].append(pos)

        for name, positions in char_positions.items():
            rows.append({
                "book_id":              book_id,
                "character_name":       name,
                "mention_count":        len(positions),
                "first_appearance_pct": min(positions),
                "last_appearance_pct":  max(positions),
                "peak_presence_pct":    max(set(positions), key=positions.count),
            })

    return rows


def write_characters(bq: bigquery.Client, rows: list[dict]):
    if not rows:
        log.info("No character rows to write.")
        return
    table_id = f"{BQ_PROJECT}.{BQ_DATASET}.characters"
    job = bq.load_table_from_json(rows, table_id)
    job.result()
    if job.errors:
        log.error(f"BigQuery errors: {job.errors}")
    else:
        log.info(f"Written {len(rows)} character rows → {table_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-id", type=str, default=None, help="Process a single book by ID")
    parser.add_argument("--dry-run", action="store_true", help="Print rows instead of writing to BigQuery")
    args = parser.parse_args()

    bq = bigquery.Client(project=BQ_PROJECT)

    log.info("Fetching arc data from BigQuery...")
    arcs = fetch_arcs(bq, book_id=args.book_id)
    log.info(f"  {len(arcs)} arc rows fetched")

    rows = compute_characters(arcs)
    log.info(f"  {len(rows)} character rows computed")

    if args.dry_run:
        import json
        print(json.dumps(rows[:10], indent=2))
    else:
        write_characters(bq, rows)


if __name__ == "__main__":
    main()
