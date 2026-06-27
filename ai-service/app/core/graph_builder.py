import os
import json
import logging
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)


class GraphBuilder:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def _get_client(self):
        if self.client is None:
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY environment variable is not set")
            self.client = Groq(api_key=self.groq_api_key)
        return self.client

    async def generate_knowledge_graph(
        self,
        topics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate knowledge graph relations between topics.

        Args:
            topics: List of topic dicts with id, title, description

        Returns:
            List of relation dicts with source_topic_id, target_topic_id,
            relationship_type, strength, description
        """
        if len(topics) < 2:
            return []

        relations = []

        # Generate pairs and batch them for efficiency
        pairs = []
        for i in range(len(topics)):
            for j in range(i + 1, len(topics)):
                pairs.append((topics[i], topics[j]))

        # Process in batches of 10
        batch_size = 10
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]
            batch_relations = await self._process_batch(batch)
            relations.extend(batch_relations)

        return relations

    async def _process_batch(
        self,
        pairs: List[tuple]
    ) -> List[Dict[str, Any]]:
        """Process a batch of topic pairs to determine relationships."""

        # Build prompt for batch
        topics_info = []
        for i, (t1, t2) in enumerate(pairs):
            topics_info.append(f"Pair {i + 1}: {t1['title']} <-> {t2['title']}")
            if t1.get('description'):
                topics_info.append(f"  {t1['title']}: {t1['description']}")
            if t2.get('description'):
                topics_info.append(f"  {t2['title']}: {t2['description']}")

        prompt = f"""Given these topic pairs, determine their relationships. Respond ONLY with a JSON array (no markdown, no explanation).

Each relation should have:
- source_topic_id: ID of the source topic
- target_topic_id: ID of the target topic
- relationship_type: RELATED, PREREQUISITE, EXTENDS, or CONTRASTS
- strength: float 0.0-1.0 (how strong is this relationship)
- description: one-line explanation of the relationship

Relationship types:
- RELATED: Topics are related but not in a specific hierarchy
- PREREQUISITE: One topic is needed to understand the other
- EXTENDS: One topic builds upon or expands the other
- CONTRASTS: Topics are opposites or have conflicting concepts

Topic pairs to analyze:
{chr(10).join(topics_info)}

Respond with ONLY a JSON array."""

        try:
            chat_completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a knowledge graph expert. Analyze topic pairs and determine their relationships."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            response_text = chat_completion.choices[0].message.content

            # Parse JSON response
            relations = json.loads(response_text)

            # Validate and clean up relations
            valid_relations = []
            for rel in relations:
                if all(k in rel for k in ["source_topic_id", "target_topic_id", "relationship_type"]):
                    rel["strength"] = min(1.0, max(0.0, float(rel.get("strength", 0.5))))
                    rel["relationship_type"] = rel["relationship_type"].upper()
                    if rel["relationship_type"] not in ["RELATED", "PREREQUISITE", "EXTENDS", "CONTRASTS"]:
                        rel["relationship_type"] = "RELATED"
                    valid_relations.append(rel)

            return valid_relations

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return []

    def generate_relations_sync(
        self,
        topics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for generate_knowledge_graph."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.generate_knowledge_graph(topics))


# Global instance
graph_builder = GraphBuilder()
