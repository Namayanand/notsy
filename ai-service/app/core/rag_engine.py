import os
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from urllib.parse import quote
from groq import Groq

from app.core.learning_modes import get_mode_config, build_system_prompt
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class RAGEngine:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self.model = "llama-3.3-70b-versatile"
        self.web_search_api_key = os.getenv("WEBSEARCH_API_KEY", "")

    def _get_client(self):
        if self.client is None:
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY environment variable is not set")
            self.client = Groq(api_key=self.groq_api_key)
        return self.client

    async def chat(
        self,
        topic_id: int,
        message: str,
        history: List[Dict[str, str]],
        learning_mode: str = "MASTER_THIS",
        use_web_search: bool = False,
        explain_depth: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_id: Optional[int] = None,
        notebook_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process a chat message using RAG.

        Returns:
            {
                "response": str,
                "sources": [{"filename": str, "chunk": str, "score": float}],
                "tokens_used": int
            }
        """
        try:
            # Get mode configuration
            mode_config = get_mode_config(learning_mode)
            top_k = mode_config.get("top_k_chunks", 5)
            use_web = use_web_search or mode_config.get("use_web", False)

            # Query vector store for relevant chunks
            query_results = vector_store.query(topic_id, message, n_results=top_k)

            documents = query_results.get("documents", [])
            metadatas = query_results.get("metadatas", [])
            distances = query_results.get("distances", [])

            sources = []
            context = ""
            has_documents = bool(documents and documents[0]) if documents else False

            # Auto-enable web search if no documents exist
            if not has_documents:
                use_web = True
                logger.info(f"No documents found for topic {topic_id}, will use web search and LLM knowledge")

            if has_documents:
                # Build context from retrieved documents
                for i, doc in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 0.0

                    # Convert distance to similarity score (ChromaDB returns L2 distance)
                    score = max(0, 1.0 - distance) if distance else 0.5

                    filename = metadata.get("source", "Unknown")
                    chunk_preview = doc[:100] + "..." if len(doc) > 100 else doc

                    sources.append({
                        "filename": filename,
                        "chunk": chunk_preview,
                        "score": round(score, 3)
                    })

                    context += f"\n\n[Source: {filename}]\n{doc}"
            else:
                # No documents found - check curated content base or web
                context = "No study material found for this topic. "

                # Try curated content base as fallback
                curated_results = self._query_curated_base(message, top_k)
                if curated_results:
                    context += "Using curated content base:\n\n" + curated_results
                elif use_web:
                    context += "Searching the web for relevant information..."
                    web_info = self._web_search(message)
                    context += "\n\n" + web_info
                else:
                    context += "Answering from general knowledge."

            # Build system prompt with optional depth context
            depth_arg: Optional[str] = explain_depth
            # Use custom system_prompt if provided (for branch context), otherwise build default
            if system_prompt:
                final_system_prompt = system_prompt
            else:
                final_system_prompt = build_system_prompt(learning_mode, context, depth_arg)

            # Build messages for Groq
            messages = [{"role": "system", "content": final_system_prompt}]

            # Add conversation history (last 10 messages)
            for msg in history[-10:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # Add current message
            messages.append({"role": "user", "content": message})

            # Call Groq API
            client = self._get_client()
            chat_completion = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=mode_config.get("temperature", 0.3),
                max_tokens=mode_config.get("max_tokens", 2000)
            )

            response = chat_completion.choices[0].message.content
            tokens_used = chat_completion.usage.total_tokens if chat_completion.usage else 0

            return {
                "response": response,
                "sources": sources,
                "tokens_used": tokens_used
            }

        except Exception as e:
            logger.error(f"Error in RAG chat: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "sources": [],
                "tokens_used": 0
            }

    async def chat_stream(
        self,
        topic_id: int,
        message: str,
        history: List[Dict[str, str]],
        learning_mode: str = "MASTER_THIS",
        use_web_search: bool = False,
        explain_depth: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream chat response token by token using SSE-compatible format.
        Yields dicts with "type" and "data" keys.
        """
        try:
            mode_config = get_mode_config(learning_mode)
            top_k = mode_config.get("top_k_chunks", 5)
            use_web = use_web_search or mode_config.get("use_web", False)

            # Query vector store
            query_results = vector_store.query(topic_id, message, n_results=top_k)

            documents = query_results.get("documents", [])
            metadatas = query_results.get("metadatas", [])
            distances = query_results.get("distances", [])

            sources = []
            context = ""
            has_documents = bool(documents and documents[0]) if documents else False

            # Auto-enable web search if no documents exist
            if not has_documents:
                use_web = True
                logger.info(f"No documents found for topic {topic_id}, will use web search and LLM knowledge")

            if has_documents:
                for i, doc in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 0.0
                    score = max(0, 1.0 - distance) if distance else 0.5
                    filename = metadata.get("source", "Unknown")
                    sources.append({
                        "filename": filename,
                        "chunk": doc[:100] + "..." if len(doc) > 100 else doc,
                        "score": round(score, 3)
                    })
                    context += f"\n\n[Source: {filename}]\n{doc}"
            else:
                context = "No study material found for this topic. "
                curated_results = self._query_curated_base(message, top_k)
                if curated_results:
                    context += "Using curated content base:\n\n" + curated_results
                elif use_web:
                    context += "Searching the web..."
                    web_info = self._web_search(message)
                    context += "\n\n" + web_info
                else:
                    context += "Answering from general knowledge."

            depth_arg: Optional[str] = explain_depth
            # Use custom system_prompt if provided (for branch context), otherwise build default
            if system_prompt:
                final_system_prompt = system_prompt
            else:
                final_system_prompt = build_system_prompt(learning_mode, context, depth_arg)

            messages = [{"role": "system", "content": final_system_prompt}]
            for msg in history[-10:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            messages.append({"role": "user", "content": message})

            # Stream the response
            client = self._get_client()
            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=mode_config.get("temperature", 0.3),
                max_tokens=mode_config.get("max_tokens", 2000),
                stream=True
            )

            full_response = ""
            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    full_response += token
                    yield {"type": "token", "data": {"token": token}}

            # Send sources after completion
            yield {"type": "sources", "data": {"sources": sources}}

            # Send done
            yield {"type": "done", "data": {
                "response": full_response,
                "tokens_used": int(len(full_response.split()) * 1.3)
            }}

        except Exception as e:
            logger.error(f"Error in streaming RAG chat: {e}")
            yield {"type": "error", "data": {"error": str(e)}}

    def _query_curated_base(self, query: str, top_k: int) -> str:
        """Query the curated content base as fallback."""
        try:
            # Query curated namespace in vector store if method exists
            if hasattr(vector_store, 'query_curated'):
                results = vector_store.query_curated(query, n_results=top_k)
                if results and results.get("documents"):
                    return "\n\n".join([
                        f"[Curated: {results['metadatas'][i].get('title', 'Unknown')}]\n{doc}"
                        for i, doc in enumerate(results["documents"])
                    ])
        except Exception as e:
            logger.error(f"Error querying curated base: {e}")
        return ""

    def _web_search(self, query: str) -> str:
        """Perform web search and return results summary."""
        try:
            import requests
            # Simple DuckDuckGo instant answer API
            url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("AbstractText"):
                    return f"[Web Search Result]\n{data['AbstractText'][:500]}"
                if data.get("RelatedTopics"):
                    topics = [t.get("Text", "") for t in data["RelatedTopics"][:3] if t.get("Text")]
                    if topics:
                        return "[Web Search Results]\n" + "\n".join(topics[:3])
            return "[No web results found]"
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return "[Web search unavailable]"

    def check_health(self) -> bool:
        """Check if the Groq API is accessible."""
        try:
            client = self._get_client()
            client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"Groq API health check failed: {e}")
            return False


# Global instance
rag_engine = RAGEngine()
