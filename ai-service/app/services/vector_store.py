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

        # Create curated base collection
        self._curated_collection_name = "curated_base"
        try:
            self.client.create_collection(name=self._curated_collection_name, metadata={})
        except Exception:
            pass

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

    def query_curated(
        self,
        query_text: str,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """Query the curated content base as fallback."""
        try:
            collection = self.client.get_collection(name=self._curated_collection_name)
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            return {
                "documents": results.get("documents", [[]])[0],
                "metadatas": results.get("metadatas", [[]])[0],
                "distances": results.get("distances", [[]])[0]
            }
        except Exception as e:
            logger.error(f"Error querying curated base: {e}")
            return {"documents": [], "metadatas": [], "distances": []}

    def semantic_search(
        self,
        query: str,
        n_results: int = 10,
        notebook_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search across all user's indexed content.
        Currently searches across all topic collections.
        """
        try:
            # Get all collections and search
            collections = self.client.list_collections()
            all_results = []

            for coll_info in collections:
                coll_name = coll_info.get("name", "")
                # Only search topic collections (not curated base)
                if coll_name.startswith("topic_") and coll_name != self._curated_collection_name:
                    try:
                        collection = self.client.get_collection(name=coll_name)
                        results = collection.query(
                            query_texts=[query],
                            n_results=n_results // 3
                        )
                        all_results.append({
                            "documents": results.get("documents", [[]])[0],
                            "metadatas": results.get("metadatas", [[]])[0],
                            "distances": results.get("distances", [[]])[0]
                        })
                    except Exception:
                        continue

            # Merge and sort by distance
            merged_docs = []
            merged_metas = []
            merged_dists = []
            for r in all_results:
                merged_docs.extend(r.get("documents", []))
                merged_metas.extend(r.get("metadatas", []))
                merged_dists.extend(r.get("distances", []))

            # Sort by distance and limit
            sorted_pairs = sorted(zip(merged_dists, merged_docs, merged_metas),
                                  key=lambda x: x[0])[:n_results]

            if sorted_pairs:
                merged_dists, merged_docs, merged_metas = zip(*sorted_pairs)
                return {
                    "documents": list(merged_docs),
                    "metadatas": list(merged_metas),
                    "distances": list(merged_dists)
                }

            return {"documents": [], "metadatas": [], "distances": []}
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return {"documents": [], "metadatas": [], "distances": []}

    def global_search(
        self,
        query: str,
        n_results: int = 10
    ) -> Dict[str, Any]:
        """Search across all content plus curated base."""
        try:
            # Search user content
            user_results = self.semantic_search(query, n_results)

            # Also search curated base
            curated_results = self.query_curated(query, n_results // 2)

            # Merge results
            all_docs = user_results.get("documents", []) + curated_results.get("documents", [])
            all_metas = user_results.get("metadatas", []) + curated_results.get("metadatas", [])
            all_dists = user_results.get("distances", []) + curated_results.get("distances", [])

            # Sort by distance
            if all_dists:
                sorted_pairs = sorted(zip(all_dists, all_docs, all_metas),
                                      key=lambda x: x[0])[:n_results]
                if sorted_pairs:
                    all_dists, all_docs, all_metas = zip(*sorted_pairs)
                    return {
                        "documents": list(all_docs),
                        "metadatas": list(all_metas),
                        "distances": list(all_dists)
                    }

            return {"documents": [], "metadatas": [], "distances": []}
        except Exception as e:
            logger.error(f"Global search error: {e}")
            return {"documents": [], "metadatas": [], "distances": []}

    def add_to_curated_base(
        self,
        chunks: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> bool:
        """Add content to the curated content base."""
        try:
            collection = self.client.get_collection(name=self._curated_collection_name)
            ids = [f"curated_{i}" for i in range(len(chunks))]
            collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(chunks)} chunks to curated base")
            return True
        except Exception as e:
            logger.error(f"Error adding to curated base: {e}")
            return False

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
