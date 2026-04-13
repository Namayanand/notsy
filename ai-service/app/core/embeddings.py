import os
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.core.document_loader import DocumentLoader
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

# Global embedding model instance
_model = None


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


class Embeddings:
    def __init__(self):
        self.model = get_embedding_model()

    def embed_resource(
        self,
        resource_id: int,
        topic_id: int,
        file_path: Optional[str],
        source_url: Optional[str],
        file_type: str,
        user_id: int
    ) -> int:
        """
        Embed a resource document into ChromaDB.
        Returns the number of chunks created.
        """
        try:
            logger.info(f"Embedding resource {resource_id} for topic {topic_id}")

            # Load document based on type
            if source_url:
                chunks_data = DocumentLoader.load_document(None, source_url, "link")
            elif file_path:
                chunks_data = DocumentLoader.load_document(file_path, None, file_type)
            else:
                raise ValueError("Either file_path or source_url must be provided")

            if not chunks_data:
                logger.warning(f"No content extracted from resource {resource_id}")
                return 0

            # Extract texts and create metadatas
            texts = [chunk["text"] for chunk in chunks_data]
            metadatas = []

            filename = os.path.basename(file_path) if file_path else source_url

            for chunk in chunks_data:
                metadata = {
                    "source": filename,
                    "page": chunk["page"],
                    "chunk_index": chunk["chunk_index"],
                    "topic_id": topic_id,
                    "resource_id": resource_id
                }
                metadatas.append(metadata)

            # Generate embeddings
            embeddings = self.model.encode(texts, show_progress_bar=False)

            # Store in ChromaDB
            success = vector_store.add_documents(topic_id, texts, metadatas)

            if success:
                chunk_count = len(texts)
                logger.info(f"Successfully embedded {chunk_count} chunks for resource {resource_id}")
                return chunk_count
            else:
                raise Exception("Failed to store documents in vector store")

        except Exception as e:
            logger.error(f"Error embedding resource {resource_id}: {e}")
            raise

    def embed_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> List[List[float]]:
        """Embed a list of texts."""
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()


# Global instance
embeddings = Embeddings()
