"""Tests for Sleuth tools — log correlation and deploy lookups."""

import json


class TestQueryIncidentMemory:
    """Test incident memory queries with empty/uninitialized store."""

    def test_empty_memory_returns_no_results(self):
        from agents.memory.vector_store import incident_store
        from agents.sleuth.tools import query_incident_memory
        result = json.loads(query_incident_memory("latency spike on inference service"))
        try:
            count = incident_store.count()
        except Exception:
            count = 0
        if count == 0:
            assert result["result_count"] == 0
        assert isinstance(result["results"], list)

    def test_memory_query_with_empty_string(self):
        from agents.sleuth.tools import query_incident_memory
        result = json.loads(query_incident_memory(""))
        assert "results" in result
