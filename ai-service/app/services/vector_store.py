import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))

    def _get_collection_name(self, topic_id: int) -> str:
        return f"topic_{topic_id}"

    def _get_or_create_collection(self, topic_id: int):
        collection_name = self._get_collection_name(topic_id)
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"topic_id": str(topic_id)}
            )
        return collection

    def add_documents(
        self,
        topic_id: int,
        chunks: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> bool:
        try:
            collection = self._get_or_create_collection(topic_id)

            ids = [f"chunk_{i}" for i in range(len(chunks))]

            collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(chunks)} chunks to topic_{topic_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding documents to topic_{topic_id}: {e}")
            return False

    def query(
        self,
        topic_id: int,
        query_text: str,
        n_results: int = 5
    ) -> Dict[str, Any]:
        try:
            collection_name = self._get_collection_name(topic_id)
            collection = self.client.get_collection(name=collection_name)

            results = collection.query(
                query_texts=[query_text],
                n_results=n_results
            )

            return {
                "documents": results.get("documents", [[]])[0],
                "metadatas": results.get("metadatas", [[]])[0],
                "distances": results.get("distances", [[]])[0],
                "ids": results.get("ids", [[]])[0]
            }
        except Exception as e:
            logger.error(f"Error querying topic_{topic_id}: {e}")
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}

    def delete_collection(self, topic_id: int) -> bool:
        try:
            collection_name = self._get_collection_name(topic_id)
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection topic_{topic_id}: {e}")
            return False

    def get_collection_count(self, topic_id: int) -> int:
        try:
            collection_name = self._get_collection_name(topic_id)
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception:
            return 0

    def collection_exists(self, topic_id: int) -> bool:
        try:
            collection_name = self._get_collection_name(topic_id)
            self.client.get_collection(name=collection_name)
            return True
        except Exception:
            return False


# Global instance
vector_store = VectorStore(
    persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
)
