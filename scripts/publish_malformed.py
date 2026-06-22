import sys
import time
from pathlib import Path
from confluent_kafka import Producer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings  # noqa: E402

TOPIC = "quality.measurements"


def main() -> None:
    producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers})

    # Intentionally malformed payload: missing required fields and invalid types
    malformed = '{"not_a_valid": true, "part_number": 12345, "timestamp": "not-a-date"}'

    producer.produce(TOPIC, key="MALFORMED-1", value=malformed)
    producer.flush(timeout=10)
    print("Published malformed message to", TOPIC)


if __name__ == '__main__':
    main()
