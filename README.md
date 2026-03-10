# Super Over

Real-time cricket dashboard that replays Cricsheet T20 match data ball-by-ball through Kafka, persists to BigQuery, and streams live updates to a React frontend via WebSockets.

## Architecture

```
Cricsheet JSON → Producer → Upstash Kafka → Consumer → BigQuery
                                                ↓
                                          Socket.IO
                                                ↓
                                        React Dashboard
```

## Project Structure

```
over/
├── terraform/          # BigQuery infrastructure (GCP)
├── producer/           # Replays Cricsheet JSON → Kafka
├── consumer/           # Kafka → BigQuery + WebSocket broadcast
├── frontend/           # React + Chart.js live dashboard
├── docker-compose.yml  # Local orchestration
└── .env.example        # Required environment variables
```

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- Terraform (optional, for BigQuery setup)
- [Upstash Kafka](https://upstash.com/) account (free tier)
- [GCP Sandbox](https://cloud.google.com/bigquery/docs/sandbox) (free, no billing required)
- A T20 match JSON from [Cricsheet](https://cricsheet.org/matches/)

## Quick Start

1. **Configure environment**
   ```bash
   cp .env.example .env
   # Fill in your Upstash Kafka and GCP credentials
   ```

2. **Download match data**

   Grab any T20 JSON from [Cricsheet Downloads](https://cricsheet.org/downloads/), unzip, and place a `.json` file in `producer/match_data/`.

3. **Provision BigQuery** (optional if using sandbox manually)
   ```bash
   cd terraform
   terraform init && terraform apply
   ```

4. **Run with Docker Compose**
   ```bash
   docker compose up --build
   ```

   - Dashboard: http://localhost:5173
   - API: http://localhost:8000

## Running Locally (without Docker)

```bash
# Terminal 1: Consumer
cd consumer
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Producer
cd producer
pip install -r requirements.txt
python main.py

# Terminal 3: Frontend
cd frontend
npm install && npm run dev
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Consumer | 8000 | FastAPI + Socket.IO server, Kafka consumer, BigQuery writer |
| Frontend | 5173 | React dashboard with live score, ball log, and run chart |
| Producer | -- | Reads Cricsheet JSON and publishes to Kafka at 1 ball/2s |
