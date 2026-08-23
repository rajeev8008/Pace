import json
import os

from confluent_kafka import Producer


JOBS_TOPIC = "productivity-jobs"
RETRY_TOPIC = "productivity-jobs-retry"
DEAD_TOPIC = "productivity-jobs-dead"


class KafkaPublisher:
    def __init__(self) -> None:
        self.producer = Producer(
            {"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")}
        )

    def publish(self, topic: str, payload: dict, key: str) -> None:
        errors = []
        self.producer.produce(
            topic,
            key=key,
            value=json.dumps(payload),
            callback=lambda error, _: errors.append(error) if error else None,
        )
        if self.producer.flush(10) or errors:
            raise RuntimeError(f"Kafka delivery failed: {errors[0] if errors else 'timeout'}")
