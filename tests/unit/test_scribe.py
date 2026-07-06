"""Tests for Scribe tools — report saving and memory storage."""

import os
import json
import tempfile
import pytest
from unittest.mock import patch

from agents.scribe.tools import save_report


class TestSaveReport:
    """Test report file writing."""

    def test_save_report_creates_file(self, tmp_path):
        reports_dir = str(tmp_path / "postmortems")
        with patch("agents.scribe.tools.REPORTS_DIR", reports_dir):
            result = json.loads(save_report("# Test Report\n\nThis is a test.", "test-123"))
            assert result["status"] == "success"
            assert result["incident_id"] == "test-123"

            filepath = os.path.join(reports_dir, "test-123.md")
            assert os.path.exists(filepath)
            with open(filepath) as f:
                assert f.read() == "# Test Report\n\nThis is a test."

    def test_save_report_with_unicode(self, tmp_path):
        reports_dir = str(tmp_path / "postmortems")
        with patch("agents.scribe.tools.REPORTS_DIR", reports_dir):
            result = json.loads(save_report("Report with émojis 🚀", "unicode-456"))
            assert result["status"] == "success"

    def test_save_report_overwrites_existing(self, tmp_path):
        reports_dir = str(tmp_path / "postmortems")
        with patch("agents.scribe.tools.REPORTS_DIR", reports_dir):
            save_report("Version 1", "overwrite-789")
            save_report("Version 2", "overwrite-789")

            filepath = os.path.join(reports_dir, "overwrite-789.md")
            with open(filepath) as f:
                assert f.read() == "Version 2"
