#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/create_bq_tables.sh <PROJECT_ID> <DATASET> [LOCATION]
# Example:
#   bash scripts/create_bq_tables.sh fsa-amadeus-471508 competitive_intel US

PROJECT_ID=${1:-${PROJECT_ID:-}}
DATASET=${2:-${BQ_DATASET:-competitive_intel}}
LOCATION=${3:-US}

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Error: PROJECT_ID is required (pass as arg1 or set env PROJECT_ID)." >&2
  exit 1
fi

echo "Project:   ${PROJECT_ID}"
echo "Dataset:   ${DATASET}"
echo "Location:  ${LOCATION}"

echo "Ensuring dataset exists..."
bq --location="${LOCATION}" mk --dataset "${PROJECT_ID}:${DATASET}" 2>/dev/null || true

echo "Creating table: ${PROJECT_ID}:${DATASET}.news_v2"
bq mk --table "${PROJECT_ID}:${DATASET}.news_v2" \
  website:STRING,url:STRING,url_hash:STRING,title:STRING,abstract:STRING,published_at:STRING 2>/dev/null || true

echo "Creating table: ${PROJECT_ID}:${DATASET}.batches_v2"
cat > /tmp/batches_v2.schema.json <<'JSON'
[
  {"name":"batch_id","type":"STRING"},
  {"name":"news_count","type":"INTEGER"},
  {"name":"run_datetime","type":"TIMESTAMP"},
  {"name":"websites","type":"RECORD","mode":"REPEATED","fields":[
    {"name":"website","type":"STRING"},
    {"name":"count","type":"INTEGER"}
  ]}
]
JSON
bq mk --table --schema=/tmp/batches_v2.schema.json "${PROJECT_ID}:${DATASET}.batches_v2" 2>/dev/null || true

echo "Creating table: ${PROJECT_ID}:${DATASET}.url_hashes"
cat > /tmp/url_hashes.schema.json <<'JSON'
[
  {"name":"website","type":"STRING"},
  {"name":"url_hashes","type":"STRING","mode":"REPEATED"},
  {"name":"batch_id","type":"STRING"},
  {"name":"run_datetime","type":"TIMESTAMP"}
]
JSON
bq mk --table --schema=/tmp/url_hashes.schema.json "${PROJECT_ID}:${DATASET}.url_hashes" 2>/dev/null || true

echo "All tables ensured. Listing dataset contents:"
bq ls "${PROJECT_ID}:${DATASET}"

