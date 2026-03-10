"""Shared Kafka producer configuration for all ingestion scripts."""

import os
import json
import logging
from confluent_kafka import Producer

logger = logging.getLogger(__name__)


def create_producer() -> Producer:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")

    config = {
        "bootstrap.servers": bootstrap,
    }

    # If Upstash creds are set, use SASL_SSL; otherwise plain (local Docker)
    if os.environ.get("UPSTASH_KAFKA_USERNAME"):
        config.update({
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "SCRAM-SHA-512",
            "sasl.username": os.environ["UPSTASH_KAFKA_USERNAME"],
            "sasl.password": os.environ["UPSTASH_KAFKA_PASSWORD"],
        })

    return Producer(config)


def delivery_callback(err, msg):
    if err:
        logger.error("Delivery failed: %s", err)
    else:
        logger.debug("Delivered to %s [%d] @ %d", msg.topic(), msg.partition(), msg.offset())


def produce_json(producer: Producer, topic: str, key: str, value: dict):
    producer.produce(
        topic,
        key=key.encode("utf-8"),
        value=json.dumps(value).encode("utf-8"),
        callback=delivery_callback,
    )
    producer.poll(0)
