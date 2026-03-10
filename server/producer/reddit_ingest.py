"""
Reddit Ingestion Producer

Queries the fh-bigquery public Reddit dataset in BigQuery for posts and comments
from book-related subreddits, then produces each record to the 'reddit-raw' Kafka topic.

The public dataset covers ~2005-2018 with monthly partitioned tables.

Usage:
    python reddit_ingest.py                    # ingest both posts and comments
    python reddit_ingest.py --comments-only    # just comments
    python reddit_ingest.py --posts-only       # just posts
    python reddit_ingest.py --dry-run          # print counts, don't produce
"""

import argparse
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.cloud import bigquery

from kafka_producer import create_producer, produce_json

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("reddit_ingest")

SUBREDDITS = [s.strip() for s in os.getenv("REDDIT_SUBREDDITS", "books,suggestmeabook,booksuggestions,literature,Fantasy,scifi,romancebooks,horrorlit,52book").split(",")]
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_REDDIT_RAW", "reddit-raw")
BATCH_SIZE = 500
BQ_PROJECT = os.getenv("GCP_PROJECT_ID")


def build_subreddit_filter() -> str:
    quoted = ", ".join(f"'{s}'" for s in SUBREDDITS)
    return f"LOWER(subreddit) IN ({quoted.lower()})"


def ingest_comments(bq_client: bigquery.Client, producer, dry_run: bool = False):
    """Query Reddit comments from book subreddits and produce to Kafka."""

    subreddit_filter = build_subreddit_filter()

    # fh-bigquery.reddit_comments has monthly tables like 2015_05
    # Wildcard query across all of them
    query = f"""
        SELECT
            id,
            subreddit,
            body,
            score,
            author,
            link_id,
            parent_id,
            created_utc
        FROM `fh-bigquery.reddit_comments.2*`
        WHERE {subreddit_filter}
          AND body IS NOT NULL
          AND body != '[deleted]'
          AND body != '[removed]'
          AND LENGTH(body) > 20
        ORDER BY created_utc ASC
    """

    logger.info("Querying Reddit comments for subreddits: %s", SUBREDDITS)

    if dry_run:
        count_query = f"""
            SELECT COUNT(*) as cnt
            FROM `fh-bigquery.reddit_comments.2*`
            WHERE {subreddit_filter}
              AND body IS NOT NULL
              AND body != '[deleted]'
              AND body != '[removed]'
        """
        results = bq_client.query(count_query).result()
        for row in results:
            logger.info("DRY RUN: Found %d comments matching filters", row.cnt)
        return

    job = bq_client.query(query)
    produced = 0

    for row in job.result(page_size=BATCH_SIZE):
        record = {
            "source": "comment",
            "id": row.id,
            "subreddit": row.subreddit,
            "body": row.body,
            "score": row.score,
            "author": row.author,
            "link_id": row.link_id,
            "parent_id": row.parent_id,
            "created_utc": row.created_utc,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        produce_json(producer, KAFKA_TOPIC, key=row.id, value=record)
        produced += 1

        if produced % 1000 == 0:
            producer.flush()
            logger.info("Produced %d comments so far...", produced)

    producer.flush()
    logger.info("Finished producing %d comments", produced)


def ingest_posts(bq_client: bigquery.Client, producer, dry_run: bool = False):
    """Query Reddit posts/submissions from book subreddits and produce to Kafka."""

    subreddit_filter = build_subreddit_filter()

    query = f"""
        SELECT
            id,
            subreddit,
            title,
            selftext,
            score,
            author,
            num_comments,
            created_utc
        FROM `fh-bigquery.reddit_posts.2*`
        WHERE {subreddit_filter}
          AND title IS NOT NULL
        ORDER BY created_utc ASC
    """

    logger.info("Querying Reddit posts for subreddits: %s", SUBREDDITS)

    if dry_run:
        count_query = f"""
            SELECT COUNT(*) as cnt
            FROM `fh-bigquery.reddit_posts.2*`
            WHERE {subreddit_filter}
              AND title IS NOT NULL
        """
        results = bq_client.query(count_query).result()
        for row in results:
            logger.info("DRY RUN: Found %d posts matching filters", row.cnt)
        return

    job = bq_client.query(query)
    produced = 0

    for row in job.result(page_size=BATCH_SIZE):
        body = row.selftext or ""
        if body in ("[deleted]", "[removed]"):
            body = ""

        record = {
            "source": "post",
            "id": row.id,
            "subreddit": row.subreddit,
            "title": row.title,
            "body": body,
            "score": row.score,
            "author": row.author,
            "num_comments": row.num_comments,
            "created_utc": row.created_utc,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        produce_json(producer, KAFKA_TOPIC, key=row.id, value=record)
        produced += 1

        if produced % 1000 == 0:
            producer.flush()
            logger.info("Produced %d posts so far...", produced)

    producer.flush()
    logger.info("Finished producing %d posts", produced)


def main():
    parser = argparse.ArgumentParser(description="Ingest Reddit book subreddit data into Kafka")
    parser.add_argument("--comments-only", action="store_true", help="Only ingest comments")
    parser.add_argument("--posts-only", action="store_true", help="Only ingest posts")
    parser.add_argument("--dry-run", action="store_true", help="Just print counts, don't produce to Kafka")
    args = parser.parse_args()

    bq_client = bigquery.Client(project=BQ_PROJECT)

    producer = None
    if not args.dry_run:
        producer = create_producer()
        logger.info("Connected to Kafka at %s", os.environ["UPSTASH_KAFKA_BOOTSTRAP"])

    logger.info("Target Kafka topic: %s", KAFKA_TOPIC)

    do_comments = not args.posts_only
    do_posts = not args.comments_only

    if do_posts:
        ingest_posts(bq_client, producer, dry_run=args.dry_run)

    if do_comments:
        ingest_comments(bq_client, producer, dry_run=args.dry_run)

    logger.info("Reddit ingestion complete.")


if __name__ == "__main__":
    main()
