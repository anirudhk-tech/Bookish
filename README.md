# Overdue -- What the Internet Actually Reads

A data pipeline that analyzes millions of Reddit book discussions, joins them with Open Library reading logs and ratings, enriches with Gutenberg readability scores, and serves insights via a real-time analytics API.

> "We analyzed millions of Reddit comments across book communities to find what the internet actually recommends. Then we checked if people follow through."

## Architecture

```
Reddit (BigQuery) ──┐
                    ├──→ Kafka ──→ Kotlin Stream Processor ──→ BigQuery ──→ FastAPI
Open Library Dumps ─┘         (enrich, extract, normalize)        │
Project Gutenberg ──────────────────────────────────────────────→─┘
```

## Key Insights

- **Reddit's Real Canon** -- the most recommended books across r/suggestmeabook, r/books, and more
- **Follow-Through Index** -- what % of "want-to-read" books actually get finished?
- **Hype vs Reality** -- do Reddit darlings rate well, or is there a gap between buzz and quality?
- **Genre Waves** -- which genres are rising and falling in internet book culture over time?

## Tech Stack

| Tool | Role |
|------|------|
| **Python** | Data ingestion (producer), analytics API (FastAPI) |
| **Kotlin** | Stream processor -- validates, enriches, extracts book mentions |
| **Kafka** | Event bus (Upstash, SASL_SSL) |
| **BigQuery** | Data warehouse -- raw events, enriched dimensions, analytics views |
| **Terraform** | GCP infrastructure as code |
| **Docker** | Containerized services, local orchestration |
| **GitLab CI/CD** | Lint, test, build, deploy pipeline |
| **GCP** | Cloud platform |

## Project Structure

```
overdue/
├── server/
│   ├── terraform/           # BigQuery dataset, tables, GCS bucket, service account
│   ├── producer/            # Python: Reddit → Kafka
│   ├── stream-processor/    # Kotlin: Kafka → enrich → BigQuery
│   ├── api/                 # Python FastAPI: analytics endpoints over BigQuery
│   ├── scripts/             # BigQuery SQL views, one-off data prep
│   ├── requirements.txt     # Shared Python dependencies
│   └── .env.example         # Required credentials template
├── client/                  # Frontend (coming soon)
├── docker-compose.yml       # Local orchestration
├── .gitlab-ci.yml           # CI/CD pipeline
└── README.md
```

## Data Sources

- **Reddit** -- posts and comments from book subreddits via BigQuery public dataset (`fh-bigquery.reddit_*`)
- **Open Library** -- reading logs (want-to-read / currently-reading / already-read) and ratings dumps from archive.org
- **Project Gutenberg** -- 68,000+ book metadata via Gutendex API; CORGIS classics dataset for pre-computed readability scores

## Quick Start

1. **Configure environment**
   ```bash
   cp server/.env.example server/.env
   # Fill in Upstash Kafka and GCP credentials
   ```

2. **Install Python dependencies**
   ```bash
   cd server && pip install -r requirements.txt
   ```

3. **Provision infrastructure**
   ```bash
   cd server/terraform && terraform init && terraform apply
   ```

4. **Run with Docker Compose**
   ```bash
   docker compose up --build
   ```

5. **Ingest data**
   ```bash
   cd server && python -m producer.reddit_ingest
   ```

6. **Query the API**
   ```bash
   curl http://localhost:8000/api/canon?limit=25
   curl http://localhost:8000/api/genre-waves
   curl http://localhost:8000/api/hype-check?title=Dune
   ```

## Running Locally (without Docker)

```bash
# Install dependencies
cd server && pip install -r requirements.txt

# Terminal 1: Kotlin stream processor
cd server/stream-processor && ./gradlew run

# Terminal 2: Analytics API
cd server && uvicorn api.main:app --port 8000

# Terminal 3: Run an ingestion job
cd server && python -m producer.reddit_ingest
```
