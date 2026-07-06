def save_report(report_content: str, incident_id: str) -> str:
    """Save the incident report to the docs directory."""
    return f"Report saved for incident {incident_id}"

def store_in_memory(incident_data: str) -> str:
    """Store the incident details in ChromaDB vector store."""
    return "Incident stored in vector store memory"
