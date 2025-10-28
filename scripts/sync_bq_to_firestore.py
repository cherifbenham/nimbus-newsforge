#!/usr/bin/env python
"""
Sync recent articles from BigQuery news_v2 into Firestore 'news' collection.

Usage examples:
  # Last 7 days (default)
  python scripts/sync_bq_to_firestore.py

  # Specific window (UTC)
  python scripts/sync_bq_to_firestore.py --start 2025-09-01T00:00:00Z --end 2025-09-09T23:59:00Z

Requires GOOGLE_APPLICATION_CREDENTIALS and PROJECT_ID/.env to be set so
google-cloud libraries can authenticate and utils can init Vertex env (no calls made).
"""
import argparse
import datetime as dt
import hashlib
import os
from typing import Optional

from google.cloud import bigquery, firestore

# Load .env if present (dev convenience)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except Exception:
    pass


def parse_iso(s: str) -> dt.datetime:
    s = s.strip()
    # Try common formats
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    # Fallback to fromisoformat with Z -> +00:00
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo:
        d = d.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return d


def run_sync(start: Optional[str], end: Optional[str]) -> None:
    project_id = os.getenv("PROJECT_ID")
    dataset = os.getenv("BQ_DATASET", "competitive_intel")
    news_table = os.getenv("BQ_NEWS_TABLE_ID", f"{project_id}.{dataset}.news_v2")

    # Date window defaults: last 7 days (UTC)
    now = dt.datetime.utcnow()
    start_dt = parse_iso(start) if start else (now - dt.timedelta(days=7))
    end_dt = parse_iso(end) if end else now

    # Query BigQuery, published_at is stored as STRING 'YYYY-MM-DD HH:MM'
    # Use PARSE_TIMESTAMP to filter correctly
    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT website, url, title, abstract, published_at, url_hash
        FROM `{news_table}`
        WHERE PARSE_TIMESTAMP('%Y-%m-%d %H:%M', published_at) BETWEEN @start_ts AND @end_ts
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_ts", "TIMESTAMP", start_dt),
            bigquery.ScalarQueryParameter("end_ts", "TIMESTAMP", end_dt),
        ]
    )
    print(f"Querying {news_table} for {start_dt.isoformat()} -> {end_dt.isoformat()} ...")
    rows = client.query(query, job_config=job_config).result()

    db = firestore.Client(project=project_id)
    batch = db.batch()
    count = 0
    for row in rows:
        url = row.url
        if not url:
            continue
        # Firestore doc id is the sha256(url) in the app
        url_hash = row.url_hash or hashlib.sha256(url.encode()).hexdigest()
        doc_ref = db.collection("news").document(url_hash)

        # Parse published_at back to datetime (naive UTC)
        published_at = None
        try:
            published_at = dt.datetime.strptime(row.published_at, "%Y-%m-%d %H:%M")
        except Exception:
            published_at = None

        data = {
            "website": row.website,
            "published_at": published_at,
            "title": row.title,
            "abstract": row.abstract,
            "full_text": "",
            "url": url,
        }
        batch.set(doc_ref, data, merge=True)
        count += 1
        # Commit in chunks to avoid overly large batches
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()

    if count % 400 != 0:
        batch.commit()

    print(f"Synced {count} documents into Firestore 'news'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync BigQuery news_v2 rows into Firestore 'news' collection")
    parser.add_argument("--start", help="ISO start datetime, e.g. 2025-09-01T00:00:00Z", default=None)
    parser.add_argument("--end", help="ISO end datetime, e.g. 2025-09-09T23:59:00Z", default=None)
    args = parser.parse_args()
    run_sync(args.start, args.end)

