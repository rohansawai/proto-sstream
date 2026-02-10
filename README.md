# CDC Stream

A Change Data Capture (CDC) system that captures database changes in real-time and enables controlled replay of historical events.

## What It Does

1. **Captures database changes** from PostgreSQL using logical replication (WAL streaming)
2. **Streams changes** through dual storage:
   - **Redis Streams** — Low-latency access for real-time consumers
   - **Apache Kafka** — Durable archival for replay and analytics
3. **Replays historical events** via gRPC with time range selection
4. **Manages replay jobs** through a Django admin dashboard

## Architecture

```
┌────────────┐     ┌───────────┐     ┌─────────────┐     ┌────────────┐
│ PostgreSQL │────▶│  Ingestor │────▶│    Redis    │────▶│   Worker   │
│   (WAL)    │     │           │     │  (fast)     │     │            │
└────────────┘     │           │     └─────────────┘     └────────────┘
                   │           │
                   │           │     ┌─────────────┐     ┌────────────┐
                   │           │────▶│    Kafka    │────▶│  Consumer  │
                   └───────────┘     │  (durable)  │     │            │
                                     └─────────────┘     └────────────┘

┌────────────┐     ┌───────────┐
│   Django   │────▶│  Replayer │
│   Admin    │gRPC │  (gRPC)   │
└────────────┘     └───────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Source Database | PostgreSQL 15 with logical replication |
| Message Queue (Fast) | Redis 7 Streams |
| Message Queue (Durable) | Apache Kafka |
| Serialization | Protocol Buffers (Protobuf) |
| Service Communication | gRPC |
| Admin Dashboard | Django 4.2 |
| Language | Python 3.11+ |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+

### Option 1: Run Everything with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

Open Django Admin: http://localhost:8001/admin (admin/admin)

### Option 2: Run Locally

```bash
# Start infrastructure
docker-compose up -d postgres redis kafka

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generate Protobuf files
python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/cdc.proto

# Terminal 1: Ingestor
python ingestor.py

# Terminal 2: Worker
python worker.py

# Terminal 3: Replayer
python replayer.py

# Terminal 4: Django Admin
cd control
python manage.py runserver 8001
```

### Create Test Data

```bash
# Create table (first time only)
docker exec -it cdc-stream-postgres psql -U repluser -d shadowdb -c \
  "CREATE TABLE events (id SERIAL PRIMARY KEY, name TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW());"

# Insert test data
docker exec -it cdc-stream-postgres psql -U repluser -d shadowdb -c \
  "INSERT INTO events (name) VALUES ('test event');"
```

## Usage

### Real-time Streaming

1. Start the ingestor and worker
2. Insert/update/delete data in PostgreSQL
3. Watch changes appear in worker output

### Replay Historical Events

1. Open Django Admin: http://localhost:8001/admin
2. Go to **Replay Jobs** → **Add Replay Job**
3. Set time range and speed factor
4. Save, select the job, and run "Run selected replay jobs"
5. Watch events replay in the Replayer terminal

### 1. Change Data Capture

The ingestor connects to PostgreSQL using a **logical replication slot** with the `test_decoding` output plugin. This streams every INSERT, UPDATE, and DELETE as it happens.

### 2. Dual Pipeline

Each change is:
- Serialized to **Protobuf** for efficient binary encoding
- Pushed to **Redis Streams** for low-latency access
- Pushed to **Kafka** for durable archival

### 3. Consumption

- **Worker** reads from Redis Streams in real-time
- **Kafka Consumer** reads from Kafka (can replay from any offset)

### 4. Replay

The Django admin:
1. Queries Redis for events in a time range
2. Sends each event to the gRPC Replayer
3. Replayer processes and logs the event (extensible to write to target DB)

## License

MIT
