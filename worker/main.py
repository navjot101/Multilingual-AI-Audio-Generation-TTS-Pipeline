import json
import os
import time
import logging
from kafka import KafkaConsumer
from prometheus_client import Histogram, start_http_server
from rag.indexer import ContextIndex
from rag.retriever import retrieve
from llm.generator import generate_story
from parser.script_parser import parse_script
from tts.synthesizer import synthesize_segments
from tts.audio_stitcher import stitch_audio
import redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("worker")

METRICS_PORT = int(os.getenv("WORKER_METRICS_PORT", "8000"))
TOPIC = "audio-generation-tasks"
CONTEXTS_PATH = os.path.join(
    os.path.dirname(__file__), "rag", "contexts", "seed_contexts.json"
)
PROCESSING_DURATION = Histogram(
    "worker_processing_duration_seconds",
    "Time spent processing a single audio generation task",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)


def main():
    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    shared_path = os.getenv("SHARED_AUDIO_PATH", "/shared/audio")

    log.info("Building RAG index from %s", CONTEXTS_PATH)
    context_index = ContextIndex(CONTEXTS_PATH)

    log.info("Connecting to Redis at %s:%d", redis_host, redis_port)
    redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    redis_client.ping()

    log.info("Connecting to Kafka at %s", kafka_bootstrap)
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=kafka_bootstrap,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="audio-worker",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    log.info("Starting Prometheus metrics server on port %d", METRICS_PORT)
    start_http_server(METRICS_PORT)

    log.info("Worker started, waiting for messages on topic '%s'", TOPIC)
    for msg in consumer:
        task = msg.value
        task_id = task["task_id"]
        log.info("Received task %s", task_id)

        try:
            redis_client.set(f"task:{task_id}:status", "PROCESSING", ex=86400)

            with PROCESSING_DURATION.time():
                context_chunks = retrieve(
                    context_index, f"{task['script']} {task.get('genre', 'general')}"
                )
                log.info(
                    "Retrieved %d context chunks for task %s",
                    len(context_chunks),
                    task_id,
                )

                story = generate_story(
                    script=task["script"],
                    genre=task.get("genre", "general"),
                    language=task.get("language", "en"),
                    context_chunks=context_chunks,
                )
                log.info("Generated story for task %s (%d chars)", task_id, len(story))

                segments = parse_script(story)
                log.info("Parsed %d segments for task %s", len(segments), task_id)

                if not segments:
                    raise ValueError("No valid [SPEAKER][EMOTION] segments found in LLM output")

                segment_paths = synthesize_segments(
                    segments, task_id, task.get("language", "en")
                )
                log.info(
                    "Synthesized %d audio segments for task %s",
                    len(segment_paths),
                    task_id,
                )

                output_path = stitch_audio(segment_paths, task_id, shared_path)
                log.info("Task %s complete — audio written to %s", task_id, output_path)

                redis_client.set(f"task:{task_id}:status", "DONE", ex=86400)

        except Exception as e:
            log.error("Task %s failed: %s", task_id, e, exc_info=True)
            redis_client.set(f"task:{task_id}:status", "FAILED", ex=86400)
            redis_client.set(f"task:{task_id}:error", str(e), ex=86400)


if __name__ == "__main__":
    main()
