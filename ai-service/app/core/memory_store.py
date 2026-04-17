import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory fallback")

try:
    from app.core.embeddings import embedding_model
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("Embeddings not available for memory store")


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
    """Shared memory system with short-term (Redis) and long-term (vector) storage"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.in_memory = InMemoryStore()
        self._connected = False

    async def connect(self):
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            logger.info("Using in-memory store (Redis not available)")
            self._connected = True
            return

        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = await redis.from_url(
                redis_url,
                decode_responses=True,
                encoding="utf-8"
            )
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            logger.info("Connected to Redis for memory store")
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. Using in-memory fallback.")
            self._connected = False

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    # Short-term memory (session context)
    async def set_session_context(self, session_id: str, key: str, value: Any, ttl: int = 3600):
        """Store session context in short-term memory"""
        if self._connected and self.redis_client:
            try:
                await self.redis_client.setex(
                    f"session:{session_id}:{key}",
                    ttl,
                    json.dumps(value, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis error, using in-memory: {e}")
                await self.in_memory.set_session_context(session_id, key, value, ttl)
        else:
            await self.in_memory.set_session_context(session_id, key, value, ttl)

    async def get_session_context(self, session_id: str, key: str) -> Any:
        """Retrieve session context from short-term memory"""
        if self._connected and self.redis_client:
            try:
                data = await self.redis_client.get(f"session:{session_id}:{key}")
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis error, using in-memory: {e}")

        return await self.in_memory.get_session_context(session_id, key)

    async def get_all_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get all context for a session"""
        if self._connected and self.redis_client:
            try:
                keys = []
                async for key in self.redis_client.scan_iter(f"session:{session_id}:*"):
                    keys.append(key)

                result = {}
                for key in keys:
                    data = await self.redis_client.get(key)
                    if data:
                        short_key = key.split(":")[-1]
                        result[short_key] = json.loads(data)
                return result
            except Exception as e:
                logger.warning(f"Redis error, using in-memory: {e}")

        return await self.in_memory.get_all_session_context(session_id)

    async def update_session_context(self, session_id: str, updates: Dict[str, Any], ttl: int = 3600):
        """Update multiple session context values"""
        for key, value in updates.items():
            await self.set_session_context(session_id, key, value, ttl)

    # Long-term memory (PostgreSQL + ChromaDB)
    async def write(self, user_id: int, memory_type: str, content: str,
                   metadata: Optional[Dict[str, Any]] = None):
        """Store memory with embedding in long-term memory"""
        if not EMBEDDINGS_AVAILABLE:
            logger.warning("Embeddings not available, storing without embedding")
            return {"stored": False, "reason": "embeddings unavailable"}

        try:
            embedding = embedding_model.encode(content)

            # Store in ChromaDB under user's memory collection
            from app.services.vector_store import vector_store

            collection_name = f"memory_{user_id}"
            vector_store.add(
                documents=[content],
                metadatas=[{
                    "memory_type": memory_type,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **(metadata or {})
                }],
                embeddings=[embedding]
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
        if not EMBEDDINGS_AVAILABLE:
            logger.warning("Embeddings not available for retrieval")
            return []

        try:
            embedding = embedding_model.encode(query)
            from app.services.vector_store import vector_store

            collection_name = f"memory_{user_id}"

            # Build filter if memory_types specified
            where_filter = None
            if memory_types:
                where_filter = {"memory_type": {"$in": memory_types}}

            results = vector_store.query_by_embedding(
                collection_name=collection_name,
                embedding=embedding,
                n_results=n_results,
                where=where_filter
            )

            memories = []
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [{}])[0]
            distances = results.get("distances", [[]])[0]

            for i, doc in enumerate(documents):
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

            # Calculate improvement trend (mock for now)
            improvement_trend = [75, 68, 72, 80, 85, 78, 82, 88]

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