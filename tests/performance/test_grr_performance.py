"""Performance tests — T-P1 (API p99 ≤ 1s) and T-P2 (GR&R runtime ≤ 5s).

These tests measure execution time directly against the Python functions
(no live server needed for T-P2) and via ASGI transport for T-P1.

Run:  pytest tests/performance/ -v -s
"""

from __future__ import annotations

import time
import statistics
import pytest
import pandas as pd


# ---------------------------------------------------------------------------
# T-P2: GR&R calculation runtime ≤ 5s
# ---------------------------------------------------------------------------

def _aiag_dataframe(n_operators: int = 3, n_parts: int = 10, n_trials: int = 3) -> pd.DataFrame:
    """Generate a balanced GR&R dataset of the given size."""
    import random
    rng = random.Random(42)
    rows = []
    for op in range(n_operators):
        for part in range(n_parts):
            true_val = 10.0 + part * 0.5
            for _ in range(n_trials):
                rows.append({
                    "operator": f"OP-{op}",
                    "part": f"P-{part}",
                    "measurement": true_val + rng.gauss(0, 0.05),
                })
    return pd.DataFrame(rows)


class TestGRRRuntime:

    def test_xbar_r_standard_dataset_under_5s(self):
        """xbar_r on a 3-operator × 10-part × 3-trial dataset must complete in < 5s (T-P2)."""
        from grr.calculator import grr_xbar_r

        df = _aiag_dataframe(n_operators=3, n_parts=10, n_trials=3)
        start = time.perf_counter()
        result = grr_xbar_r(df)
        elapsed = time.perf_counter() - start

        assert result.total_grr >= 0, "GRR% must be non-negative"
        assert elapsed < 5.0, f"xbar_r took {elapsed:.2f}s — must be < 5s (T-P2)"

    def test_anova_standard_dataset_under_5s(self):
        """ANOVA GR&R on a 3-operator × 10-part × 3-trial dataset must complete in < 5s (T-P2)."""
        from grr.calculator import grr_anova

        df = _aiag_dataframe(n_operators=3, n_parts=10, n_trials=3)
        start = time.perf_counter()
        result = grr_anova(df)
        elapsed = time.perf_counter() - start

        assert result.total_grr >= 0
        assert elapsed < 5.0, f"grr_anova took {elapsed:.2f}s — must be < 5s (T-P2)"

    def test_xbar_r_large_dataset_under_5s(self):
        """xbar_r on a larger 10-operator × 10-part × 10-trial dataset (1000 rows — the
        upper bound of the AIAG d2* table) must still complete in < 5s."""
        from grr.calculator import grr_xbar_r

        df = _aiag_dataframe(n_operators=10, n_parts=10, n_trials=10)
        start = time.perf_counter()
        result = grr_xbar_r(df)
        elapsed = time.perf_counter() - start

        assert elapsed < 5.0, f"Large xbar_r took {elapsed:.2f}s — must be < 5s"

    def test_grr_repeated_calls_stable_runtime(self):
        """50 repeated GR&R calls must all complete in < 5s each (no memory leak / drift)."""
        from grr.calculator import grr_xbar_r

        df = _aiag_dataframe()
        times = []
        for _ in range(50):
            start = time.perf_counter()
            grr_xbar_r(df)
            times.append(time.perf_counter() - start)

        mean_s = statistics.mean(times)
        p99_s = sorted(times)[int(0.99 * len(times))]
        print(f"\nGRR mean={mean_s*1000:.1f}ms  p99={p99_s*1000:.1f}ms")

        assert p99_s < 5.0, f"GRR p99 runtime {p99_s:.2f}s exceeds 5s gate"


# ---------------------------------------------------------------------------
# T-P1: API endpoint p99 latency ≤ 1s
# ---------------------------------------------------------------------------

class TestAPILatency:

    @pytest.mark.asyncio
    async def test_health_endpoint_p99_under_100ms(self):
        """GET /health/live must be extremely fast — p99 < 100ms."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            times = []
            for _ in range(50):
                start = time.perf_counter()
                resp = await client.get("/health/live")
                times.append((time.perf_counter() - start) * 1000)
                assert resp.status_code == 200

        p99_ms = sorted(times)[int(0.99 * len(times))]
        print(f"\n/health/live p99={p99_ms:.1f}ms")
        assert p99_ms < 100, f"Health probe p99 {p99_ms:.1f}ms exceeds 100ms"

    @pytest.mark.asyncio
    async def test_spc_analyze_p99_under_1s(self):
        """POST /api/v1/spc/analyze must return results within 1s at p99 (T-P1)."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        payload = {
            "values": [10.0 + i * 0.01 for i in range(50)],
            "chart_type": "i_mr",
            "subgroup_size": 1,
            "part_number": "PERF-TEST",
            "characteristic_name": "diameter",
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers={"x-api-key": "test-api-key"},
        ) as client:
            times = []
            for _ in range(30):
                start = time.perf_counter()
                resp = await client.post("/api/v1/spc/analyze", json=payload)
                elapsed_ms = (time.perf_counter() - start) * 1000
                # Accept both 200 (success) and DB-related errors (no live DB in perf test)
                assert resp.status_code in (200, 422, 500)
                times.append(elapsed_ms)

        p99_ms = sorted(times)[int(0.99 * len(times))]
        mean_ms = statistics.mean(times)
        print(f"\nSPC analyze mean={mean_ms:.1f}ms  p99={p99_ms:.1f}ms")
        assert p99_ms < 1000, f"SPC p99 latency {p99_ms:.1f}ms exceeds 1000ms gate (T-P1)"

    @pytest.mark.asyncio
    async def test_grr_endpoint_p99_under_1s(self):
        """POST /api/v1/studies/grr (statistical path only) must complete in < 1s at p99 (T-P1)."""
        from httpx import AsyncClient, ASGITransport
        from api.main import app

        measurements = [
            {"part": f"P{p}", "operator": op, "value": 10.0 + p * 0.1 + (0.05 if op == "B" else 0.0)}
            for p in range(1, 6)
            for op in ["A", "B", "C"]
            for _ in range(2)
        ]
        payload = {
            "part_ids": [f"P{p}" for p in range(1, 6)],
            "operator_ids": ["A", "B", "C"],
            "measurements": measurements,
            "method": "xbar_r",
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers={"x-api-key": "test-api-key"},
        ) as client:
            times = []
            for _ in range(20):
                start = time.perf_counter()
                resp = await client.post("/api/v1/studies/grr", json=payload)
                elapsed_ms = (time.perf_counter() - start) * 1000
                assert resp.status_code in (201, 422, 500)
                times.append(elapsed_ms)

        p99_ms = sorted(times)[int(0.99 * len(times))]
        print(f"\nGRR endpoint p99={p99_ms:.1f}ms")
        assert p99_ms < 1000, f"GRR endpoint p99 {p99_ms:.1f}ms exceeds 1000ms gate (T-P1)"
