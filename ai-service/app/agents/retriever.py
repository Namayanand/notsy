import logging
from typing import Dict, Any, Optional, List

from app.agents.base import BaseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class RetrieverAgent(BaseAgent):
    """Agent that handles semantic search and RAG"""

    name = "retriever"
    description = "Handles semantic search and RAG"

    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the retriever agent"""
        query = input.payload.get("query")
        topic_id = input.payload.get("topic_id")
        notebook_id = input.payload.get("notebook_id")

        # Get current topic if no query
        if not query:
            topic = input.context.get("current_topic")
            if topic:
                query = f"explain {topic}"

        if not query:
            return AgentOutput(
                agent_type=self.name,
                result={"error": "No query provided"},
                next_agent=None,
                metadata={"error": True}
            )

        logger.info(f"Retriever: Searching for: {query}")

        # Perform semantic search
        results = await self._perform_search(query, topic_id, notebook_id, input.user_id)

        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        if not documents or not documents[0]:
            # Try global search as fallback
            logger.info("No topic-specific results, trying global search")
            results = await self._global_search(query)
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])

        # Build sources for context
        sources = self._build_sources(documents, metadatas, results.get("distances", []))

        # Store retrieved content in context
        from app.core.memory_store import memory_store
        try:
            await memory_store.set_session_context(
                input.session_id,
                "retrieved_sources",
                sources,
                ttl=3600
            )
        except Exception:
            pass

        return AgentOutput(
            agent_type=self.name,
            result={
                "query": query,
                "sources": sources,
                "result_count": len(sources)
            },
            next_agent="tutor",
            metadata={"result_count": len(sources)}
        )

    async def _perform_search(self, query: str, topic_id: Optional[int],
                             notebook_id: Optional[int], user_id: int) -> Dict:
        """Perform semantic search"""
        if topic_id:
            try:
                results = await self.execute_tool(
                    "search_notes",
                    query=query,
                    topic_id=topic_id,
                    n_results=5
                )
                return results
            except Exception as e:
                logger.warning(f"Topic search failed: {e}")

        if notebook_id:
            try:
                results = await self.execute_tool(
                    "semantic_search",
                    query=query,
                    notebook_id=notebook_id,
                    user_id=user_id,
                    n_results=10
                )
                return results
            except Exception as e:
                logger.warning(f"Notebook search failed: {e}")

        return {"documents": [], "metadatas": [], "distances": []}

    async def _global_search(self, query: str) -> Dict:
        """Perform global semantic search"""
        try:
            results = await self.execute_tool(
                "semantic_search",
                query=query,
                n_results=10
            )
            return results
        except Exception as e:
            logger.warning(f"Global search failed: {e}")
            return {"documents": [], "metadatas": [], "distances": []}

    def _build_sources(self, documents: List, metadatas: List, distances: List) -> List[Dict]:
        """Build source list for context"""
        sources = []
        has_docs = documents and documents[0] if documents else False

        if has_docs:
            for i, doc in enumerate(documents):
                if not doc:
                    continue

                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0
                score = max(0, 1.0 - distance)

                source = {
                    "content": doc[:500] + "..." if len(doc) > 500 else doc,
                    "filename": metadata.get("source", "Unknown"),
                    "score": round(score, 3),
                    "metadata": metadata
                }
                sources.append(source)

        return sources