import argparse
import random
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings  # noqa: E402
from schemas.measurement import MeasurementEvent  # noqa: E402


TOPIC = "quality.measurements"
EVENTS_TOPIC = "quality.events"
DLQ_TOPIC = "quality.measurements.dlq"


# ─── Topic provisioning ───────────────────────────────────────────────────────

def ensure_topics(bootstrap_servers: str) -> None:
    """Create required Kafka topics if they do not already exist."""
    admin = AdminClient({"bootstrap.servers": bootstrap_servers})
    existing = set(admin.list_topics(timeout=10).topics.keys())

    to_create = []
    for topic_name in (TOPIC, EVENTS_TOPIC, DLQ_TOPIC):
        if topic_name not in existing:
            to_create.append(NewTopic(topic_name, num_partitions=1, replication_factor=1))

    if not to_create:
        print(f"Topics {TOPIC!r} and {EVENTS_TOPIC!r} already exist.")
        return

    results = admin.create_topics(to_create)
    for topic_name, future in results.items():
        try:
            future.result()
            print(f"Topic {topic_name!r} ready.")
        except Exception as exc:
            # Topic may have been created concurrently — not fatal.
            print(f"Could not create topic {topic_name!r}: {exc}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish synthetic quality measurements to Kafka.")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--delay-ms", type=int, default=100)
    parser.add_argument("--bootstrap-servers", default=settings.kafka_bootstrap_servers)
    parser.add_argument("--equipment-id", default="CMM-001")
    return parser.parse_args()


# ─── Record builder ───────────────────────────────────────────────────────────

def build_event(index: int, equipment_id: str) -> MeasurementEvent:
    """Build and validate a MeasurementEvent; raises ValidationError if invalid."""
    measured_value = 25.25 if index % 200 == 0 else round(random.normalvariate(25.0, 0.03), 4)

    return MeasurementEvent(
        timestamp=datetime.now(UTC),
        part_number=f"PART-{index:06d}",
        characteristic_name="diameter",
        nominal_value=25.0,
        measured_value=measured_value,
        unit="mm",
        operator_id=f"OP-{(index % 5) + 1:03d}",
        equipment_id=equipment_id,
        shift=["A", "B", "C"][index % 3],
        event_id=uuid.uuid4().hex,
    )


# ─── Delivery callback ────────────────────────────────────────────────────────

def delivery_report(error, message) -> None:
    if error is not None:
        print(f"Delivery failed for record key {message.key()}: {error}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    ensure_topics(args.bootstrap_servers)

    producer = Producer({"bootstrap.servers": args.bootstrap_servers})
    delay_seconds = args.delay_ms / 1000
    start_time = time.perf_counter()

    for index in range(1, args.count + 1):
        event = build_event(index, args.equipment_id)  # ValidationError raised here if invalid
        producer.produce(
            TOPIC,
            key=event.part_number,
            value=event.model_dump_json(),  # Pydantic serialisation (datetime → ISO string)
            callback=delivery_report,
        )
        producer.poll(0)

        if index % 100 == 0:
            print(f"Published {index}/{args.count}...")

        if index < args.count:
            time.sleep(delay_seconds)

    producer.flush()
    elapsed_seconds = time.perf_counter() - start_time
    print(f"Published total {args.count} records in {elapsed_seconds:.2f} seconds")


if __name__ == "__main__":
    main()
