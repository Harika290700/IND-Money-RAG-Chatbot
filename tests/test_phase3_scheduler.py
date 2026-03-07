"""
Phase 3 tests: Config and run_once entry point.
- Config loads from env.
- run_once returns 0 or 1 (we mock pipeline to avoid running Phase 1 in unit test).
"""
import os
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.mark.phase3
class TestPhase3Config:
    def test_config_loads(self):
        from phase3 import config
        assert hasattr(config, "PIPELINE_MODE")
        assert config.PIPELINE_MODE in ("full", "from_json")
        assert hasattr(config, "TIMEOUT_SEC")
        assert hasattr(config, "RETRIES")
        assert hasattr(config, "PHASE2_BACKEND_URL")
        assert hasattr(config, "SCHEDULE_TIME")

    def test_config_schedule_time_format(self):
        from phase3.config import SCHEDULE_TIME
        # Should be HH:MM-like
        assert ":" in SCHEDULE_TIME or SCHEDULE_TIME.isdigit()


@pytest.mark.phase3
class TestPhase3RunOnce:
    """Test run_once module; mock pipeline to avoid running Phase 1."""

    def test_run_with_timeout_returns_bool_when_mocked(self):
        from phase3 import run_once
        with patch.object(run_once, "_run_pipeline"):
            result = run_once.run_with_timeout()
        assert result is True

    def test_main_returns_int(self):
        from phase3.run_once import main
        # Mock so pipeline "succeeds" and we get exit 0
        with patch("phase3.run_once.run_with_timeout", return_value=True), \
             patch("phase3.run_once._notify_refresh_complete", return_value=True):
            code = main()
        assert code == 0

    def test_main_returns_1_on_failure(self):
        from phase3.run_once import main
        with patch("phase3.run_once.run_with_timeout", return_value=False):
            code = main()
        assert code == 1
