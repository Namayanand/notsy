import os
import logging
from typing import List, Dict, Any, Optional
from groq import Groq

from app.core.learning_modes import get_mode_config, build_system_prompt
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class RAGEngine:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self.model = "llama3-70b-8192"

    def _get_client(self):
        if self.client is None:
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY environment variable is not set")
            self.client = Groq(api_key=self.groq_api_key)
        return self.client

    def chat(
        self,
        topic_id: int,
        message: str,
        history: List[Dict[str, str]],
        learning_mode: str = "MASTER_THIS"
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

            # Query vector store for relevant chunks
            query_results = vector_store.query(topic_id, message, n_results=top_k)

            documents = query_results.get("documents", [])
            metadatas = query_results.get("metadatas", [])
            distances = query_results.get("distances", [])

            sources = []
            context = ""

            if documents:
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
                # No documents found - answer from general knowledge
                context = "No study material found for this topic. Answering from general knowledge."

            # Build system prompt
            system_prompt = build_system_prompt(learning_mode, context)

            # Build messages for Groq
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history (last 10 messages)
            for msg in history[-10:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # Add current message
            messages.append({"role": "user", "content": message})

            # Call Groq API
            chat_completion = self._get_client().chat.completions.create(
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

    def check_health(self) -> bool:
        """Check if the Groq API is accessible."""
        try:
            # Simple completion test
            self.client.chat.completions.create(
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
