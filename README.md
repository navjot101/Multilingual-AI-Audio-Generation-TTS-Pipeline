# Multilingual AI Audio Generation Pipeline

An **asynchronous, production-grade audio story generation backend** that turns a short text prompt into a fully-produced dramatic audio file. Submit a premise, get back a task ID, and poll until your AI-narrated `.wav` file is ready.

## Architecture

```
Client ──HTTP──▶ Gateway (Java 21 / Spring Boot)
                    │
                    ├──▶ Kafka ──▶ Worker (Python 3.11)
                    │                 │
                    │                 ├── RAG (FAISS + sentence-transformers)
                    │                 ├── LLM (Groq / DeepSeek)
                    │                 ├── TTS (gTTS)
                    │                 └── Audio Stitcher (pydub + ffmpeg)
                    │
                    └──▶ Redis (task status)
```

A client submits a prompt → Gateway publishes a task to Kafka and returns a `task_id` → the Worker picks it up, retrieves relevant context (RAG), generates a dramatic script via an LLM, converts each line to speech with gTTS, and stitches everything into a single `.wav` file → the Client polls for status and downloads the result.

## Features

- **Async by design** — no blocking; get an immediate task ID and poll
- **Multilingual TTS** — supports English, Hindi, Tamil, German, French
- **RAG-enhanced** — FAISS vector index injects relevant world lore into LLM prompts
- **Swappable LLMs** — Groq (free) or DeepSeek
- **Dramatic scripts** — LLM generates speaker + emotion tags for a radio-play effect
- **Observability** — Prometheus metrics on both Gateway and Worker
- **Fully containerized** — Docker Compose with 5 services

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Gateway API | Java 21, Spring Boot 3.2, Maven |
| Worker | Python 3.11 |
| Message Queue | Apache Kafka (KRaft mode, no Zookeeper) |
| State Store | Redis 7 |
| LLM Providers | Groq (`llama3-70b-8192`) or DeepSeek (`deepseek-chat`) |
| TTS Engine | Google Text-to-Speech (gTTS) — free, no API key |
| Vector Search | FAISS + sentence-transformers (`all-MiniLM-L6-v2`) |
| Audio Processing | pydub + ffmpeg |
| Monitoring | Prometheus |

## Quick Start

### Prerequisites

- Docker Desktop (with WSL2 backend on Windows)
- A free API key from [Groq](https://console.groq.com/keys)

### Setup

```bash
# Clone the repo
git clone https://github.com/navjot101/Multilingual-AI-Audio-Generation-TTS-Pipeline.git
cd Multilingual-AI-Audio-Generation-TTS-Pipeline

# Create environment file
cp .env.example .env

# Edit .env and set your API key
#   LLM_PROVIDER=groq
#   GROQ_API_KEY=gsk_your-actual-key

# Build and start all services
docker-compose up --build -d
```

First build takes 3–5 minutes (Maven downloads dependencies, Python installs packages).

### Generate Audio

```bash
# Submit a story premise
curl -s -X POST http://localhost:8080/v1/audio/generate \
  -H "Content-Type: application/json" \
  -d '{"script":"A detective walks into a rain-soaked Mumbai alley.","genre":"thriller","language":"en"}'

# Response:
# {
#   "task_id": "8f3b9a1c-...",
#   "status": "PENDING",
#   "poll_url": "/v1/audio/status/8f3b9a1c-...",
#   "download_url": "/v1/audio/download/8f3b9a1c-..."
# }

# Poll until status is DONE
curl http://localhost:8080/v1/audio/status/8f3b9a1c-...

# Download the .wav file
curl -o output.wav http://localhost:8080/v1/audio/download/8f3b9a1c-...
```

## API Reference

All endpoints under `/v1/audio`.

### `POST /v1/audio/generate`

Submit a generation task.

**Request Body:**
```json
{
  "script": "A detective walks into a rain-soaked Mumbai alley.",
  "genre": "thriller",
  "language": "en"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `script` | string | yes | — | Story premise / prompt |
| `genre` | string | no | `general` | Used for RAG context retrieval |
| `language` | string | no | `en` | `en`, `hi`, `ta`, `de`, `fr` |

**Response** `202 Accepted`:
```json
{
  "task_id": "uuid",
  "status": "PENDING",
  "poll_url": "/v1/audio/status/uuid",
  "download_url": "/v1/audio/download/uuid"
}
```

### `GET /v1/audio/status/{taskId}`

Poll task status. Returns `PENDING | PROCESSING | DONE | FAILED`.

### `GET /v1/audio/download/{taskId}`

Download the generated `.wav` file (returns `409` if not yet `DONE`).

### `GET /actuator/health`

Health check endpoint.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | yes | `groq` | `groq` or `deepseek` |
| `GROQ_API_KEY` | with Groq | — | [Groq console](https://console.groq.com/keys) |
| `DEEPSEEK_API_KEY` | with DeepSeek | — | [DeepSeek platform](https://platform.deepseek.com) |
| `KAFKA_BOOTSTRAP` | no | `kafka:9092` | Kafka broker address |
| `REDIS_HOST` | no | `redis` | Redis hostname |
| `REDIS_PORT` | no | `6379` | Redis port |
| `SHARED_AUDIO_PATH` | no | `/shared/audio` | Volume path for `.wav` output |

## Project Structure

```
├── docker-compose.yml       # 5 services: kafka, redis, gateway, worker, prometheus
├── gateway/                  # Java Spring Boot REST API
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/main/java/com/audiopipeline/
│       ├── controller/       # REST endpoints
│       ├── model/            # Request/response DTOs
│       ├── service/          # Kafka producer, Redis status
│       └── config/           # Kafka, Redis config
├── worker/                   # Python ML pipeline
│   ├── Dockerfile
│   ├── main.py               # Kafka consumer + orchestrator
│   ├── llm/generator.py      # Groq / DeepSeek integration
│   ├── tts/
│   │   ├── synthesizer.py    # gTTS per segment
│   │   └── audio_stitcher.py # pydub concatenation
│   ├── rag/
│   │   ├── indexer.py        # FAISS index builder
│   │   ├── retriever.py      # Vector search
│   │   └── contexts/         # Seed story knowledge base
│   └── parser/               # Script tag extraction
├── infra/
│   ├── kafka/                # KRaft config
│   ├── redis/                # Redis config
│   └── prometheus/           # Prometheus config
└── .env.example              # Environment variable template
```

## Worker Pipeline (End-to-End)

```
Kafka message received
  → Redis: status = PROCESSING
  → RAG: retrieve top-3 context chunks from FAISS index
  → LLM: generate dramatic script with [SPEAKER][EMOTION] tags
  → Parser: extract tagged segments via regex
  → TTS: synthesize each segment with gTTS
  → Stitcher: concatenate with 300ms silence → .wav
  → Redis: status = DONE
```

## Useful Commands

```bash
# View logs
docker-compose logs -f worker
docker-compose logs -f gateway

# Stop everything
docker-compose down

# Rebuild after code changes
docker-compose up --build -d
```

## License

MIT
