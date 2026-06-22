"""Cleanup script to remove created DB files for test verification.

Deletes `data/quality_control.db` and any `test_quality.db` files under the system temp directory.
Reports successes and failures.
"""
from pathlib import Path
import tempfile
import glob
import os

results = []
# data DB
data_db = Path(__file__).resolve().parents[1] / 'data' / 'quality_control.db'
if data_db.exists():
    try:
        data_db.unlink()
        results.append(f"deleted {data_db}")
    except Exception as e:
        results.append(f"failed to delete {data_db}: {e}")
else:
    results.append(f"not found {data_db}")

# temp test DBs
tmpdir = os.getenv('TMP') or tempfile.gettempdir()
found = glob.glob(os.path.join(tmpdir, '**', 'test_quality.db'), recursive=True)
if not found:
    results.append('no test_quality.db files found in tmp')
else:
    for f in found:
        p = Path(f)
        try:
            p.unlink()
            results.append(f"deleted {p}")
        except Exception as e:
            results.append(f"failed to delete {p}: {e}")

print('\n'.join(results))
