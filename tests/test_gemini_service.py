import os
import pytest

from backend.services import gemini_service as gs


def test_gemini_service_raises_without_key():
    # Ensure GEMINI_API_KEY is not set
    os.environ.pop("GEMINI_API_KEY", None)

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        gs.analyze_grr_sync({"dummy": "data"})
