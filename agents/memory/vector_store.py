"""ChromaDB vector store for incident memory — used by Sleuth and Scribe."""

import logging
from typing import Optional

logger = logging.getLogger("aegis.memory.vector_store")


class IncidentVectorStore:
    """Wrapper around ChromaDB for storing and querying past incidents.

    Provides semantic search over historical incidents so Sleuth can find
    patterns and similar events when diagnosing new anomalies.
    """

    def __init__(self, persist_dir: str = "./chroma_db", collection_name: str = "incidents"):
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._client = None
        self._collection = None

    def _ensure_initialized(self):
        """Lazy initialization — only connects to ChromaDB when first used."""
        if self._client is not None:
            return

        try:
            import os

            import chromadb
            if "VERCEL" in os.environ:
                self._client = chromadb.EphemeralClient()
            else:
                self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"description": "Aegis incident history for semantic search"},
            )
            logger.info(
                "ChromaDB initialized: persist_dir=%s, collection=%s, count=%d",
                self._persist_dir, self._collection_name, self._collection.count(),
            )
        except Exception as exc:
            logger.error("Failed to initialize ChromaDB: %s", exc)
            raise

    def add_incident(
        self,
        incident_id: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add an incident to the vector store.

        Args:
            incident_id: Unique identifier for the incident.
            text: Full text description (used for embedding).
            metadata: Optional metadata dict (must be flat str/int/float values).
        """
        self._ensure_initialized()
        # ChromaDB metadata must be flat key-value pairs
        clean_metadata = {}
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_metadata[k] = v
                else:
                    clean_metadata[k] = str(v)[:500]

        self._collection.upsert(
            ids=[incident_id],
            documents=[text],
            metadatas=[clean_metadata] if clean_metadata else None,
        )
        logger.info("Stored incident %s in vector store (text length: %d)", incident_id, len(text))

    def search_similar(self, query: str, k: int = 5) -> list[dict]:
        """Search for incidents similar to the query text.

        Args:
            query: Natural language description of the incident/symptoms.
            k: Number of results to return.

        Returns:
            List of dicts with 'id', 'text', 'distance', and 'metadata' fields.
        """
        self._ensure_initialized()
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(k, self._collection.count()),
        )

        output = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"][0]):
                entry = {
                    "id": doc_id,
                    "text": results["documents"][0][i] if results.get("documents") else "",
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                }
                if results.get("metadatas") and results["metadatas"][0][i]:
                    entry["metadata"] = results["metadatas"][0][i]
                output.append(entry)

        return output

    def count(self) -> int:
        """Return the number of incidents in the store."""
        self._ensure_initialized()
        return self._collection.count()


# Module-level singleton — lazy-initialized on first use
incident_store = IncidentVectorStore()
