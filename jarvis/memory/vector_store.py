from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
try:
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except Exception:  # pragma: no cover - optional dependency
    HAS_SENTENCE_TRANSFORMERS = False

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None
        self.collection = None
        self.embedding_model = None
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        try:
            self.client = chromadb.PersistentClient(
                path=str(Path(self.settings.memory.path).expanduser()),
                settings=ChromaSettings(anonymized_telemetry=False),
            )

            self.collection = self.client.get_or_create_collection(
                name=self.settings.memory.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

            # Don't load the embedding model here — lazy-load it on first use
            # to reduce startup time (model loading takes 20-30s).
            self._initialized = True
            logger.info("Vector store initialized (embedding model will lazy-load on first search)")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")

    async def _ensure_embedding_model(self) -> bool:
        """Lazy-load the sentence-transformers embedding model on first use."""
        if self.embedding_model is not None:
            return True
        if not HAS_SENTENCE_TRANSFORMERS:
            logger.warning("sentence-transformers not available; semantic search disabled")
            return False
        try:
            self.embedding_model = SentenceTransformer(self.settings.memory.embedding_model)
            logger.info("Embedding model loaded: %s", self.settings.memory.embedding_model)
            return True
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            return False

    async def add_memory(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            raise RuntimeError("Vector store not initialized")

        memory_id = str(uuid.uuid4())
        if not await self._ensure_embedding_model():
            raise RuntimeError("Embedding model unavailable; cannot add memory")

        embedding = self.embedding_model.encode(content).tolist()

        meta = {
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }

        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[meta],
        )

        return memory_id

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            return []

        if not await self._ensure_embedding_model():
            logger.warning("Search skipped: embedding model unavailable")
            return []

        query_embedding = self.embedding_model.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
        )

        memories = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                memories.append({
                    "id": memory_id,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": 1 - results["distances"][0][i] if results["distances"] else 0,
                })

        return memories

    async def list_memories(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            return []

        results = self.collection.get(limit=limit)

        memories = []
        if results["ids"]:
            for i, memory_id in enumerate(results["ids"]):
                memories.append({
                    "id": memory_id,
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i],
                    "timestamp": results["metadatas"][i].get("timestamp", ""),
                })

        return memories

    async def delete_memory(self, memory_id: str) -> bool:
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            return False

        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False