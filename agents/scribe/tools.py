"""Scribe tools — save reports and store incidents in vector memory."""

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("aegis.scribe.tools")

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs", "postmortems")


def save_report(report_content: str, incident_id: str) -> str:
    """Save the incident postmortem report as a markdown file.

    Writes the report to docs/postmortems/{incident_id}.md for permanent
    archival and easy review.
    """
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filename = f"{incident_id}.md"
        filepath = os.path.join(REPORTS_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info("Report saved: %s", filepath)
        return json.dumps({
            "status": "success",
            "action": "save_report",
            "incident_id": incident_id,
            "filepath": filepath,
            "size_bytes": len(report_content),
        })
    except Exception as exc:
        logger.error("Failed to save report for %s: %s", incident_id, exc)
        return json.dumps({
            "status": "failed",
            "action": "save_report",
            "incident_id": incident_id,
            "error": str(exc),
        })


def store_in_memory(incident_data: str) -> str:
    """Store the incident details in ChromaDB vector store for future retrieval.

    Indexes the incident text so that Sleuth can find similar historical
    incidents when diagnosing new anomalies.
    """
    try:
        from agents.memory.vector_store import incident_store

        # Parse incident data to extract an ID
        try:
            data = json.loads(incident_data)
            incident_id = data.get("id", f"incident_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
            # Build a text summary for embedding
            summary_parts = []
            if "anomaly" in data:
                a = data["anomaly"]
                summary_parts.append(f"Service: {a.get('service', 'unknown')}, Metric: {a.get('metric', 'unknown')}")
            if "diagnosis" in data and data["diagnosis"]:
                summary_parts.append(f"Root cause: {data['diagnosis'].get('root_cause', 'unknown')}")
            if "action" in data and data["action"]:
                summary_parts.append(f"Action: {data['action'].get('description', 'unknown')}")
            text = ". ".join(summary_parts) if summary_parts else incident_data
        except (json.JSONDecodeError, KeyError):
            incident_id = f"incident_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            text = incident_data

        incident_store.add_incident(
            incident_id=incident_id,
            text=text,
            metadata={"raw": incident_data[:2000]},  # truncate metadata to stay under limits
        )

        logger.info("Incident %s stored in vector memory", incident_id)
        return json.dumps({
            "status": "success",
            "action": "store_in_memory",
            "incident_id": incident_id,
        })
    except Exception as exc:
        logger.warning("Failed to store in memory: %s", exc)
        return json.dumps({
            "status": "failed",
            "action": "store_in_memory",
            "error": str(exc),
            "note": "Vector store may not be initialized. Incident was still processed.",
        })
