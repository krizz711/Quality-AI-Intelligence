"""
Smoke test — run a GR&R study through QualityOrchestrator.

Usage:
  poetry run python scripts/smoke_test_orchestrator_grr.py
"""

import asyncio
import json

from agent.orchestrator import QualityOrchestrator

event = {
    "study_type": "grr",
    "equipment_id": "CMM-001",
    "characteristic_name": "diameter",
    "measurements": [
        {"part": "P1", "operator": "A", "value": 0.29},
        {"part": "P1", "operator": "A", "value": 0.41},
        {"part": "P2", "operator": "A", "value": -0.56},
        {"part": "P2", "operator": "A", "value": -0.68},
        {"part": "P3", "operator": "A", "value": 1.34},
        {"part": "P3", "operator": "A", "value": 1.17},
        {"part": "P1", "operator": "B", "value": 0.08},
        {"part": "P1", "operator": "B", "value": 0.25},
        {"part": "P2", "operator": "B", "value": -0.47},
        {"part": "P2", "operator": "B", "value": -1.22},
        {"part": "P3", "operator": "B", "value": 1.19},
        {"part": "P3", "operator": "B", "value": 0.94},
        {"part": "P1", "operator": "C", "value": 0.04},
        {"part": "P1", "operator": "C", "value": 0.34},
        {"part": "P2", "operator": "C", "value": -1.38},
        {"part": "P2", "operator": "C", "value": -1.13},
        {"part": "P3", "operator": "C", "value": 0.88},
        {"part": "P3", "operator": "C", "value": 1.09},
    ],
}


async def main() -> None:
    orchestrator = QualityOrchestrator()
    result = await orchestrator.handle_measurement_event(event)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
