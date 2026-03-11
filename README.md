# Overdue — The Shape of Every Story

A narrative analytics engine that processes thousands of books from Project Gutenberg through an NLP pipeline, extracts tension curves, character arcs, and conflict patterns, and lets you explore and compare the structure of stories interactively.

> "Every story has a shape. We make them visible."

---

## What It Does

Overdue ingests full book texts, splits them into sections, runs NLP analysis on each section, and stores the results in a data warehouse. The frontend lets you:

- Browse a catalog of thousands of books with **tension curve sparklines** as previews
- Open any book and see its **full narrative arc** — sentiment, tension, character presence, pacing — annotated with key plot moments
- **Compare books side by side** — overlay their curves to see how different authors structure stories
- Explore **cross-book insights** powered by BigQuery — genre tension fingerprints, era comparisons, author signatures
- **Upload your own PDF** and compare it against the Gutenberg catalog

---

## Architecture

```
Gutenberg API ──→ Ingester ──→ GCS (raw texts)
                     │
                     └──→ Kafka: books-to-process
                                     │
                              Chunker (Python)
                                     │
                              Kafka: book-chunks
                                     │
                            NLP Worker (Python)
                          (sentiment, tension, NER)
                                     │
                              Kafka: arc-events
                                     │
                        Stream Processor (Kotlin)
                        (aggregate, validate, sink)
                                     │
                                 BigQuery
                                     │
                              FastAPI (Python)
                                     │
                            Vite Frontend (client)
```

---

## Tech Stack

| Tool | Role |
|------|------|
| **Python** | Gutenberg ingestion, text chunking, NLP workers (spaCy, Transformers) |
| **Kotlin** | Stream processor — consumes arc events from Kafka, aggregates, writes to BigQuery |
| **Kafka** | Pipeline backbone connecting all processing stages |
| **BigQuery** | Data warehouse for arc data, cross-book analytics queries |
| **GCS** | Raw book text storage |
| **Terraform** | All GCP infrastructure as code |
| **Docker** | Containerized services, local orchestration |
| **GitLab CI/CD** | Lint, test, build, deploy pipeline |
| **GCP** | Cloud platform (BigQuery, GCS, Cloud Run) |
| **Vite** | Interactive frontend |

---

## Data Pipeline

### Stage 1 — Ingest
The **Ingester** (Python) fetches the Gutenberg catalog via the Gutendex API, downloads full book texts, stores them in GCS, and produces book IDs to the `books-to-process` Kafka topic.

### Stage 2 — Chunk
The **Chunker** (Python) consumes from `books-to-process`, reads the raw text from GCS, and splits it into sections. Chapters are detected first (by "Chapter X" patterns); if no chapters are found, the text is split into fixed-size windows (~500 words) with overlap. Each chunk is produced to the `book-chunks` Kafka topic with its position metadata.

### Stage 3 — Analyze
The **NLP Worker** (Python) consumes from `book-chunks` and runs:

- **Sentiment scoring** — a transformer-based sentiment model scores each chunk on a continuous scale (positive ↔ negative)
- **Tension scoring** — composite of: sentiment volatility in a rolling window, negative sentiment intensity, conflict keyword density (fight, death, betrayal, etc.), and dialogue density
- **Character extraction** — spaCy NER identifies PERSON entities per chunk; character presence is tracked across the full book
- **Pacing score** — sentence length variance and dialogue-to-narration ratio

Results are produced to the `arc-events` Kafka topic.

### Stage 4 — Sink
The **Stream Processor** (Kotlin) consumes from `arc-events`, validates and aggregates results per book, and writes to BigQuery.

---

## BigQuery Schema

### `books`
Book metadata dimension table.

| Column | Type | Description |
|--------|------|-------------|
| `book_id` | STRING | Gutenberg ID |
| `title` | STRING | |
| `author` | STRING | |
| `genre` | STRING | Primary genre |
| `subjects` | STRING REPEATED | All subject tags |
| `language` | STRING | |
| `publish_year` | INTEGER | |
| `word_count` | INTEGER | Full text length |
| `gcs_path` | STRING | Raw text location in GCS |
| `processed_at` | TIMESTAMP | Last NLP run |

### `book_arcs`
Core NLP results — one row per chunk per book.

| Column | Type | Description |
|--------|------|-------------|
| `book_id` | STRING | |
| `chunk_index` | INTEGER | Sequential chunk number |
| `position_pct` | FLOAT | 0.0–1.0 position in book |
| `chapter` | STRING | Chapter label if detected |
| `word_count` | INTEGER | Chunk size |
| `sentiment_score` | FLOAT | -1.0 (negative) to 1.0 (positive) |
| `tension_score` | FLOAT | 0.0–1.0 composite tension |
| `pacing_score` | FLOAT | 0.0–1.0 (slow to fast) |
| `conflict_density` | FLOAT | Conflict keyword ratio |
| `dominant_characters` | STRING REPEATED | Top characters in this chunk |

*Partitioned by book_id, clustered on chunk_index.*

### `characters`
Per-book character presence data.

| Column | Type | Description |
|--------|------|-------------|
| `book_id` | STRING | |
| `character_name` | STRING | As extracted by NER |
| `mention_count` | INTEGER | Total across book |
| `first_appearance_pct` | FLOAT | Where they enter the story |
| `last_appearance_pct` | FLOAT | Where they exit |
| `peak_presence_pct` | FLOAT | Position of most mentions |

---

## Kafka Topics

| Topic | Producer | Consumer | Partitions | Payload |
|-------|----------|----------|------------|---------|
| `books-to-process` | Ingester | Chunker | 1 | `{ book_id, title, gcs_path }` |
| `book-chunks` | Chunker | NLP Worker | 8 | `{ book_id, chunk_index, position_pct, text, chapter }` |
| `arc-events` | NLP Worker | Stream Processor (Kotlin) | 8 | `{ book_id, chunk_index, sentiment_score, tension_score, ... }` |

Messages on `book-chunks` and `arc-events` are produced with no partition key, so Kafka distributes them evenly across all 8 partitions. Ordering within a book is not required at processing time — each chunk carries `book_id` and `chunk_index`, and the arc is reassembled in order by BigQuery at read time.

---

## Frontend

### Library View
Grid of book cards. Each card shows title, author, genre, and a **sparkline of the tension curve** — so you can see the shape of a story before clicking. Filterable by genre, era, and language. Searchable by title/author.

### Book Detail View
Full-page arc visualization for a single book:
- **Main graph** — tension curve across the full book, X-axis is position (%), Y-axis is score. Annotated with chapter markers and detected peak moments.
- **Sentiment track** — emotional tone across the book, overlaid or in a separate lane
- **Character presence** — stacked/swimlane view of when each major character is active
- **Pacing track** — fast vs. slow sections highlighted
- Hover over any point to see the actual text snippet from that section

### Compare Mode
Select 2–4 books and overlay their tension curves on the same graph. Color-coded per book. Useful for genre comparisons, same-author comparisons, or classic vs. modern.

### Explore View
BigQuery-powered cross-book analytics:
- Average tension curve by genre (Gothic horror vs. Romance vs. Adventure)
- Tension curve similarity clusters — books grouped by story shape, not genre label
- Author signature charts — how a given author's tension patterns vary across their catalog
- Era trends — do Victorian novels build tension differently than 20th century ones?

### Upload a PDF
Drop in any book PDF. The backend extracts text, runs it through the same NLP pipeline (via a direct processing job, not Kafka), stores results, and renders the arc. Compare against the Gutenberg baseline.

---

## Project Structure

```
overdue/
├── server/
│   ├── terraform/           # GCP infra: BigQuery, GCS, Cloud Run, service accounts
│   ├── ingester/            # Python: Gutenberg catalog + text → GCS + Kafka
│   ├── chunker/             # Python: GCS text → Kafka book-chunks
│   ├── nlp-worker/          # Python: NLP analysis → Kafka arc-events
│   ├── stream-processor/    # Kotlin: Kafka arc-events → BigQuery sink
│   ├── api/                 # Python FastAPI: arc data + analytics endpoints
│   ├── scripts/             # BigQuery SQL views and one-off queries
│   ├── requirements.txt
│   └── .env.example
├── client/                  # Vite frontend
├── docker-compose.yml       # Local orchestration
├── .gitlab-ci.yml           # CI/CD pipeline
└── README.md
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/books` | Paginated book catalog with genre/era filters |
| `GET /api/books/{id}` | Book metadata |
| `GET /api/books/{id}/arc` | Full arc data (all chunks) |
| `GET /api/books/{id}/characters` | Character presence data |
| `GET /api/compare?ids=1,2,3` | Arc data for multiple books |
| `GET /api/explore/genres` | Average tension curves by genre |
| `GET /api/explore/authors/{name}` | Author arc signature across their catalog |
| `POST /api/upload` | Upload a PDF for processing |

---

## Local Kafka Setup

Kafka runs on a separate machine on your local network via Docker. Only one config change is needed — the host machine needs to advertise its LAN IP so other machines on the network can connect.

**On the Kafka host machine:**
```bash
# Find the LAN IP (e.g. 192.168.1.50)
ipconfig getifaddr en0

# Set it and start Kafka
KAFKA_HOST_IP=192.168.1.50 docker compose up -d kafka
```

**On your dev machine**, set `KAFKA_BOOTSTRAP` in `server/.env`:
```
KAFKA_BOOTSTRAP=192.168.1.50:9092
```

That's it — no auth needed on a local network, it's PLAINTEXT.

---

## Quick Start

1. **Configure environment**
   ```bash
   cp server/.env.example server/.env
   # Fill in GCP, Kafka bootstrap, and GCS credentials
   ```

2. **Provision infrastructure**
   ```bash
   cd server/terraform && terraform init && terraform apply
   ```

3. **Start Kafka** (on the host machine, see Local Kafka Setup above)

4. **Run the pipeline**
   ```bash
   docker compose run ingester python -m ingester.main --limit 100
   ```

5. **Start the frontend**
   ```bash
   cd client && npm install && npm run dev
   ```

---

## Data Source

**Project Gutenberg** via the [Gutendex API](https://gutendex.com) — 70,000+ public domain books with full text downloads, structured metadata (title, author, subjects, languages), and no API key required.
