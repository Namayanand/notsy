import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Flag for embeddings - will be lazily initialized
EMBEDDINGS_AVAILABLE = None


class InMemoryStore:
    """In-memory fallback for session storage"""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    async def set_session_context(self, session_id: str, key: str, value: Any, ttl: int = 3600):
        if session_id not in self._store:
            self._store[session_id] = {}
        self._store[session_id][key] = value

    async def get_session_context(self, session_id: str, key: str) -> Any:
        return self._store.get(session_id, {}).get(key)

    async def get_all_session_context(self, session_id: str) -> Dict[str, Any]:
        return self._store.get(session_id, {})

    async def delete_session(self, session_id: str):
        if session_id in self._store:
            del self._store[session_id]


class MemoryStore:
    """Shared memory system with in-memory short-term and vector-based long-term storage"""

    def __init__(self):
        self.in_memory = InMemoryStore()
        self._embedding_model = None

    async def connect(self):
        """Initialize the memory store"""
        logger.info("Using in-memory store for session data")

    async def disconnect(self):
        """Close connections (no-op for in-memory store)"""
        pass

    # Short-term memory (session context)
    async def set_session_context(self, session_id: str, key: str, value: Any, ttl: int = 3600):
        """Store session context in short-term memory"""
        await self.in_memory.set_session_context(session_id, key, value, ttl)

    async def get_session_context(self, session_id: str, key: str) -> Any:
        """Retrieve session context from short-term memory"""
        return await self.in_memory.get_session_context(session_id, key)

    async def get_all_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get all context for a session"""
        return await self.in_memory.get_all_session_context(session_id)

    async def update_session_context(self, session_id: str, updates: Dict[str, Any], ttl: int = 3600):
        """Update multiple session context values"""
        for key, value in updates.items():
            await self.set_session_context(session_id, key, value, ttl)

    # Long-term memory (PostgreSQL + ChromaDB)
    async def write(self, user_id: int, memory_type: str, content: str,
                   metadata: Optional[Dict[str, Any]] = None):
        """Store memory with embedding in long-term memory"""
        global EMBEDDINGS_AVAILABLE
        if EMBEDDINGS_AVAILABLE is None:
            try:
                from app.core.embeddings import get_embedding_model
                self._embedding_model = get_embedding_model()
                EMBEDDINGS_AVAILABLE = True
            except ImportError:
                EMBEDDINGS_AVAILABLE = False

        if not EMBEDDINGS_AVAILABLE:
            logger.warning("Embeddings not available, storing without embedding")
            return {"stored": False, "reason": "embeddings unavailable"}

        try:
            # Store in ChromaDB under user's memory collection
            from app.services.vector_store import vector_store

            collection_name = f"memory_{user_id}"
            # Use a dedicated memory topic ID (negative to avoid conflicts)
            memory_topic_id = -1000 - user_id
            vector_store.add_documents(
                topic_id=memory_topic_id,
                chunks=[content],
                metadatas=[{
                    "memory_type": memory_type,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    **(metadata or {})
                }]
            )

            # Also store in backend database for durability
            await self._store_in_backend(user_id, memory_type, content, metadata)

            return {"stored": True, "collection": collection_name}
        except Exception as e:
            logger.error(f"Error writing to long-term memory: {e}")
            return {"stored": False, "error": str(e)}

    async def read(self, user_id: int, query: str,
                  memory_types: Optional[List[str]] = None,
                  n_results: int = 10) -> List[Dict[str, Any]]:
        """Retrieve relevant memories from long-term memory"""
        global EMBEDDINGS_AVAILABLE
        if EMBEDDINGS_AVAILABLE is None:
            try:
                from app.core.embeddings import get_embedding_model
                self._embedding_model = get_embedding_model()
                EMBEDDINGS_AVAILABLE = True
            except ImportError:
                EMBEDDINGS_AVAILABLE = False

        if not EMBEDDINGS_AVAILABLE:
            logger.warning("Embeddings not available for retrieval")
            return []

        try:
            from app.services.vector_store import vector_store

            # Use the same memory topic ID as write
            memory_topic_id = -1000 - user_id

            results = vector_store.query(
                topic_id=memory_topic_id,
                query_text=query,
                n_results=n_results
            )

            memories = []
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[{}]])[0]
            distances = results.get("distances", [[]])[0]

            for i, doc in enumerate(documents):
                # Filter by memory_type if specified
                if memory_types:
                    mem_type = metadatas[i].get("memory_type", "") if i < len(metadatas) else ""
                    if mem_type not in memory_types:
                        continue
                memories.append({
                    "content": doc,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "similarity": 1 - distances[i] if i < len(distances) else 0
                })

            return memories
        except Exception as e:
            logger.error(f"Error reading from long-term memory: {e}")
            return []

    async def _store_in_backend(self, user_id: int, memory_type: str,
                               content: str, metadata: Optional[Dict[str, Any]] = None):
        """Store memory entry in backend database"""
        try:
            import requests
            url = os.getenv("BACKEND_URL", "http://localhost:8080")
            response = requests.post(
                f"{url}/api/memory",
                json={
                    "userId": user_id,
                    "memoryType": memory_type,
                    "content": content,
                    "metadata": metadata or {}
                },
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Could not store in backend: {e}")
            return False

    async def get_insights(self, user_id: int) -> Dict[str, Any]:
        """Generate insights from user's memory"""
        try:
            # Get all mistake memories
            mistakes = await self.read(user_id, "mistakes errors wrong answers",
                                     memory_types=["mistake"], n_results=20)

            # Get assessment memories
            assessments = await self.read(user_id, "quiz performance scores",
                                        memory_types=["assessment"], n_results=20)

            # Extract weak topics
            weak_topics = []
            for m in mistakes:
                topic = m.get("metadata", {}).get("topic", "")
                if topic:
                    weak_topics.append(topic)

            from collections import Counter
            topic_counts = Counter(weak_topics)
            top_weak = [topic for topic, count in topic_counts.most_common(5)]

            # Calculate improvement trend from real assessment scores (chronological order)
            improvement_trend = []
            for a in assessments:
                score = a.get("metadata", {}).get("score")
                if score is not None:
                    try:
                        improvement_trend.append(float(score))
                    except (TypeError, ValueError):
                        pass
            # Keep the last 20 data points; fall back to empty list (not mock data)
            improvement_trend = improvement_trend[-20:]

            return {
                "weak_topics": top_weak,
                "mistake_count": len(mistakes),
                "assessment_count": len(assessments),
                "improvement_trend": improvement_trend
            }
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {
                "weak_topics": [],
                "mistake_count": 0,
                "improvement_trend": []
            }


# Global instance
memory_store = MemoryStore()