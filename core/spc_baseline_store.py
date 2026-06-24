"""Persistence for frozen SPC baselines.

Thin async DB layer over the ``spc_baselines`` table, shared by the API
(``api.quality_routes``) and the autonomous monitor (``agent.monitor``) so both judge
measurements against the **same** locked limits — one source of truth, no divergence.

The statistical logic (computing/validating a baseline) lives in :mod:`spc.baseline`;
this module only reads and writes it.
"""

from __future__ import annotations

from db.database import AsyncSessionLocal
from db.models import SpcBaseline
from spc.baseline import Baseline


def _to_baseline(row: SpcBaseline) -> Baseline:
    return Baseline(ucl=row.ucl, cl=row.cl, lcl=row.lcl, sigma=row.sigma, n_points=row.n_points)


async def get_baseline(process_name: str) -> Baseline | None:
    """Return the frozen baseline for ``process_name``, or None if none is set."""
    async with AsyncSessionLocal() as session:
        row = await session.get(SpcBaseline, process_name)
        return _to_baseline(row) if row is not None else None


async def save_baseline(process_name: str, baseline: Baseline, *, created_by: str | None = None) -> None:
    """Insert or replace the frozen baseline for ``process_name``."""
    async with AsyncSessionLocal() as session:
        row = await session.get(SpcBaseline, process_name)
        if row is None:
            session.add(
                SpcBaseline(
                    process_name=process_name,
                    ucl=baseline.ucl,
                    cl=baseline.cl,
                    lcl=baseline.lcl,
                    sigma=baseline.sigma,
                    n_points=baseline.n_points,
                    created_by=created_by,
                )
            )
        else:
            row.ucl = baseline.ucl
            row.cl = baseline.cl
            row.lcl = baseline.lcl
            row.sigma = baseline.sigma
            row.n_points = baseline.n_points
            row.created_by = created_by
        await session.commit()


async def delete_baseline(process_name: str) -> bool:
    """Remove the frozen baseline for ``process_name``. Returns True if one existed."""
    async with AsyncSessionLocal() as session:
        row = await session.get(SpcBaseline, process_name)
        if row is None:
            return False
        await session.delete(row)
        await session.commit()
        return True
