import sys
import time
from pathlib import Path
from confluent_kafka import Consumer, KafkaException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings  # noqa: E402

DLQ_TOPIC = "quality.measurements.dlq"


def main(timeout_seconds: int = 120) -> None:
    consumer = Consumer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "group.id": "dlq-tester",
        "auto.offset.reset": "earliest",
    })

    consumer.subscribe([DLQ_TOPIC])
    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())
            print("DLQ message key:", msg.key())
            print("DLQ message value:", msg.value().decode('utf-8'))
            return
        print("No DLQ message found within timeout")
    finally:
        consumer.close()


if __name__ == '__main__':
    main()
