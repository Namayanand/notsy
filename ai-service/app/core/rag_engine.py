import os
import re
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from urllib.parse import quote
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.learning_modes import get_mode_config, build_system_prompt
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class SelfRAG:
    """Self-RAG prompt templates and utilities."""

    RETRIEVAL_PROMPT = """Given the user question, determine if you need to retrieve additional information from the knowledge base to answer accurately.

Question: {question}

Respond with EXACTLY one word: "RETRIEVE" or "NO_RETRIEVE"

- "RETRIEVE" if the question requires specific knowledge, facts, or information from study materials
- "NO_RETRIEVE" if you can answer from general knowledge or the conversation history"""

    GRADING_PROMPT = """You are a relevance grader. Evaluate each retrieved document for relevance to the user question.

Question: {question}

Retrieved Documents:
{documents}

For each document, respond with a relevance score and brief justification.
Format your response as follows:

[GRADING]
Document 1 (Source: {source1}): RELEVANT | PARTIAL | IRRELEVANT
Reason: [2-3 sentence justification]
Document 2 (Source: {source2}): RELEVANT | PARTIAL | IRRELEVANT
Reason: [2-3 sentence justification]
...

Use:
- RELEVANT: Document directly answers or contains key information for the question
- PARTIAL: Document has some related information but needs synthesis
- IRRELEVANT: Document does not help answer the question"""

    GENERATION_PROMPT = """You are generating an answer based on retrieved documents. Use ONLY the relevant documents to ground your response.

Question: {question}

Relevant Documents:
{documents}

Instructions:
1. Use information ONLY from the provided documents
2. Cite sources using [Source: filename] inline references
3. If documents don't fully answer the question, state what is missing
4. Do not hallucinate information not in the documents

Generate your response now:"""

    REVISION_PROMPT = """You are evaluating a generated response for accuracy and grounding.

Original Question: {question}

Generated Response:
{response}

Provided Documents:
{documents}

Evaluate the response:
1. Is the response grounded in the provided documents? (no hallucinations)
2. Are all claims supported by citations?
3. Is the response relevant to the question?

Respond in this format:

[EVALUATION]
Groundedness: SUPPORTED / PARTIAL / UNSUPPORTED
Citation Coverage: COMPLETE / PARTIAL / MISSING
Relevance: RELEVANT / PARTIAL / IRRELEVANT

If UNSUPPORTED or MISSING, provide a revised response:
[REVISED_RESPONSE]
[your improved response with proper citations]"""

    @staticmethod
    def parse_retrieval_decision(response: str) -> bool:
        """Parse the model's retrieval decision."""
        response = response.strip().upper()
        return "RETRIEVE" in response

    @staticmethod
    def parse_grading(response: str) -> List[Dict[str, Any]]:
        """Parse the grading response to extract relevance scores."""
        results = []
        lines = response.split('\n')
        current_doc = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Match document grading patterns
            match = re.search(r'Document\s+(\d+).*?:\s*(RELEVANT|PARTIAL|IRRELEVANT)', line, re.IGNORECASE)
            if match:
                if current_doc and 'grade' in current_doc:
                    results.append(current_doc)
                current_doc = {'grade': match.group(2).upper()}
            # Look for reason lines
            reason_match = re.search(r'Reason:\s*(.+)', line, re.IGNORECASE)
            if reason_match and current_doc:
                current_doc['reason'] = reason_match.group(1).strip()
        if current_doc and 'grade' in current_doc:
            results.append(current_doc)
        return results


class RAGEngine:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.web_search_api_key = os.getenv("WEBSEARCH_API_KEY", "")
        self.self_rag = SelfRAG()
        self.enable_self_rag = os.getenv("ENABLE_SELF_RAG", "true").lower() == "true"

    def _get_client(self):
        if self.client is None:
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY environment variable is not set")
            self.client = Groq(api_key=self.groq_api_key)
        return self.client

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def _groq_create(self, **kwargs):
        """Call Groq API with automatic exponential backoff retry."""
        return self._get_client().chat.completions.create(**kwargs)

    async def _self_rag_retrieval_decision(self, message: str) -> bool:
        """Step 1: Decide if retrieval is needed using Self-RAG."""
        try:
            prompt = SelfRAG.RETRIEVAL_PROMPT.format(question=message)
            response = self._groq_create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10
            )
            decision = response.choices[0].message.content
            return SelfRAG.parse_retrieval_decision(decision)
        except Exception as e:
            logger.error(f"Error in retrieval decision: {e}")
            return True  # Default to retrieval on error

    async def _self_rag_grade_documents(
        self,
        message: str,
        documents: List[str],
        metadatas: List[Dict]
    ) -> tuple:
        """Step 2: Grade retrieved documents for relevance."""
        try:
            docs_formatted = []
            for i, doc in enumerate(documents):
                source = metadatas[i].get("source", "Unknown") if i < len(metadatas) else "Unknown"
                docs_formatted.append(f"Document {i+1} (Source: {source}):\n{doc}")

            docs_text = "\n\n".join(docs_formatted)
            prompt = SelfRAG.GRADING_PROMPT.format(
                question=message,
                documents=docs_text,
                source1=metadatas[0].get("source", "doc1") if metadatas else "doc1",
                source2=metadatas[1].get("source", "doc2") if len(metadatas) > 1 else "doc2"
            )

            response = self._groq_create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            grading_response = response.choices[0].message.content

            # Filter to only RELEVANT and PARTIAL documents
            graded_docs = []
            graded_metadatas = []

            lines = grading_response.split('\n')
            for i, line in enumerate(lines):
                line = line.strip().upper()
                if 'RELEVANT' in line or 'PARTIAL' in line:
                    doc_idx = i - 1  # approximate mapping
                    if doc_idx >= 0 and doc_idx < len(documents):
                        graded_docs.append(documents[doc_idx])
                        if doc_idx < len(metadatas):
                            graded_metadatas.append(metadatas[doc_idx])

            # If grading failed, use all documents
            if not graded_docs:
                graded_docs = documents
                graded_metadatas = metadatas

            return graded_docs, graded_metadatas

        except Exception as e:
            logger.error(f"Error in document grading: {e}")
            return documents, metadatas

    async def _self_rag_generate(
        self,
        message: str,
        documents: List[str],
        metadatas: List[Dict],
        learning_mode: str,
        explain_depth: Optional[str] = None,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> tuple:
        """Step 3: Generate response with citations."""
        try:
            # Prepare documents with sources
            docs_with_sources = []
            for i, doc in enumerate(documents):
                source = metadatas[i].get("source", "Unknown") if i < len(metadatas) else "Unknown"
                docs_with_sources.append(f"[Source: {source}]\n{doc}")

            docs_text = "\n\n".join(docs_with_sources)
            prompt = SelfRAG.GENERATION_PROMPT.format(
                question=message,
                documents=docs_text
            )

            # Get mode config
            mode_config = get_mode_config(learning_mode)
            depth_arg = explain_depth

            # Build system prompt
            if system_prompt:
                final_system_prompt = system_prompt
            else:
                final_system_prompt = build_system_prompt(learning_mode, docs_text, depth_arg)

            # Include Self-RAG instructions in system prompt
            final_system_prompt += """

IMPORTANT: You are operating in Self-RAG mode. When answering:
1. Only use information from the provided documents
2. Always cite sources using [Source: filename] format
3. If information is not in the documents, say so explicitly"""

            messages = [{"role": "system", "content": final_system_prompt}]
            for msg in (history or [])[-10:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            messages.append({"role": "user", "content": prompt})

            chat_completion = self._groq_create(
                model=self.model,
                messages=messages,
                temperature=mode_config.get("temperature", 0.3),
                max_tokens=mode_config.get("max_tokens", 2000)
            )

            response = chat_completion.choices[0].message.content
            tokens_used = chat_completion.usage.total_tokens if chat_completion.usage else 0

            return response, tokens_used

        except Exception as e:
            logger.error(f"Error in Self-RAG generation: {e}")
            raise

    async def _self_rag_revision(
        self,
        message: str,
        response: str,
        documents: List[str],
        metadatas: List[Dict],
        max_iterations: int = 3
    ) -> tuple:
        """
        Step 4: Iteratively revise response until grounded or max iterations reached.
        Returns: (final_response, was_revised, num_iterations)
        """
        current_response = response
        num_iterations = 0

        for iteration in range(max_iterations):
            num_iterations += 1

            try:
                docs_with_sources = []
                for i, doc in enumerate(documents):
                    source = metadatas[i].get("source", "Unknown") if i < len(metadatas) else "Unknown"
                    docs_with_sources.append(f"[Source: {source}]\n{doc}")

                docs_text = "\n\n".join(docs_with_sources)

                # First, evaluate the response
                evaluation_prompt = SelfRAG.REVISION_PROMPT.format(
                    question=message,
                    response=current_response,
                    documents=docs_text
                )

                chat_completion = self._groq_create(
                    model=self.model,
                    messages=[{"role": "user", "content": evaluation_prompt}],
                    temperature=0.1,
                    max_tokens=1500
                )

                evaluation_response = chat_completion.choices[0].message.content

                # Parse evaluation results
                is_grounded, citation_complete, is_relevant = self._parse_revision_evaluation(evaluation_response)

                logger.info(f"Iteration {num_iterations}: Grounded={is_grounded}, Citations={citation_complete}, Relevant={is_relevant}")

                # If everything looks good, stop
                if is_grounded and citation_complete and is_relevant:
                    logger.info(f"Response passed evaluation after {num_iterations} iteration(s)")
                    return current_response, num_iterations > 1, num_iterations

                # If not grounded, check for revised response or generate one
                if "[REVISED_RESPONSE]" in evaluation_response:
                    revised = evaluation_response.split("[REVISED_RESPONSE]")[-1].strip()
                    current_response = revised
                    logger.info(f"Iteration {num_iterations}: Using revised response")
                else:
                    # Generate a new revision since evaluation found issues
                    revision_prompt = f"""The previous response has issues:
- Groundedness: {is_grounded}
- Citations: {citation_complete}
- Relevance: {is_relevant}

Original Question: {message}
Current Response: {current_response}
Documents: {docs_text}

Generate a revised response that:
1. Only uses information from the provided documents
2. Cites all sources using [Source: filename] format
3. Directly answers the question
4. Does not hallucinate

Respond with ONLY the revised response, no explanation."""

                    revision_completion = self._groq_create(
                        model=self.model,
                        messages=[{"role": "user", "content": revision_prompt}],
                        temperature=0.1,
                        max_tokens=1500
                    )
                    current_response = revision_completion.choices[0].message.content
                    logger.info(f"Iteration {num_iterations}: Generated new revision")

            except Exception as e:
                logger.error(f"Error in Self-RAG revision iteration {num_iterations}: {e}")
                break

        # Return the final response after all iterations
        was_revised = num_iterations > 1
        return current_response, was_revised, num_iterations

    def _parse_revision_evaluation(self, evaluation_text: str) -> tuple:
        """Parse the revision evaluation to extract groundedness, citation, relevance."""
        text = evaluation_text.upper()

        # Parse groundedness
        is_grounded = "GROUNDEDNESS: SUPPORTED" in text or "GROUNDEDNESS: PARTIAL" in text
        if "GROUNDEDNESS: UNSUPPORTED" in text:
            is_grounded = False

        # Parse citation coverage
        citation_complete = "CITATION COVERAGE: COMPLETE" in text or "CITATION COVERAGE: PARTIAL" in text
        if "CITATION COVERAGE: MISSING" in text:
            citation_complete = False

        # Parse relevance
        is_relevant = "RELEVANCE: RELEVANT" in text or "RELEVANCE: PARTIAL" in text
        if "RELEVANCE: IRRELEVANT" in text:
            is_relevant = False

        return is_grounded, citation_complete, is_relevant

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
        Process a chat message using Self-RAG pipeline.

        Returns:
            {
                "response": str,
                "sources": [{"filename": str, "chunk": str, "score": float}],
                "tokens_used": int,
                "retrieved": bool,
                "graded": bool,
                "revised": bool
            }
        """
        try:
            mode_config = get_mode_config(learning_mode)
            top_k = mode_config.get("top_k_chunks", 5)
            use_web = use_web_search or mode_config.get("use_web", False)

            # Self-RAG tracking
            retrieved = False
            graded = False
            revised = False
            total_tokens = 0

            # Step 1: Retrieval decision (if Self-RAG enabled)
            if self.enable_self_rag:
                needs_retrieval = await self._self_rag_retrieval_decision(message)
                if not needs_retrieval:
                    # No retrieval needed - answer from history/general knowledge
                    return await self._generate_without_retrieval(
                        message, history, learning_mode, explain_depth, system_prompt
                    )

            # Step 2: Retrieve documents
            query_results = vector_store.query(topic_id, message, n_results=top_k)
            documents = query_results.get("documents", [])
            metadatas = query_results.get("metadatas", [])
            distances = query_results.get("distances", [])

            has_documents = bool(documents and documents[0]) if documents else False

            if not has_documents:
                use_web = True
                logger.info(f"No documents found for topic {topic_id}, using fallback")

                # Fallback handling
                context = "No study material found for this topic. "
                curated_results = self._query_curated_base(message, top_k)
                if curated_results:
                    context += "Using curated content base:\n\n" + curated_results
                elif use_web:
                    context += "Searching the web for relevant information..."
                    web_info = self._web_search(message)
                    context += "\n\n" + web_info
                else:
                    context += "Answering from general knowledge."

                return await self._generate_with_context(
                    message, context, [], learning_mode, explain_depth, system_prompt
                )

            retrieved = True

            # Step 3: Grade documents (if Self-RAG enabled)
            if self.enable_self_rag:
                documents, metadatas = await self._self_rag_grade_documents(
                    message, documents, metadatas
                )
                graded = True

            # Build sources for response
            sources = []
            context = ""
            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 0.0
                score = max(0, 1.0 - distance) if distance else 0.5
                filename = metadata.get("source", "Unknown")
                chunk_preview = doc[:100] + "..." if len(doc) > 100 else doc
                sources.append({
                    "filename": filename,
                    "chunk": chunk_preview,
                    "score": round(score, 3)
                })
                context += f"\n\n[Source: {filename}]\n{doc}"

            # Step 4: Generate with citations
            response, gen_tokens = await self._self_rag_generate(
                message, documents, metadatas, learning_mode, explain_depth, system_prompt, history
            )
            total_tokens += gen_tokens

            # Step 5: Iterative Revision (if Self-RAG enabled)
            revision_iterations = 0
            if self.enable_self_rag:
                response, was_revised, revision_iterations = await self._self_rag_revision(
                    message, response, documents, metadatas, max_iterations=3
                )
                revised = was_revised
                total_tokens += revision_iterations * 150  # Approximate tokens per revision

            return {
                "response": response,
                "sources": sources,
                "tokens_used": total_tokens,
                "retrieved": retrieved,
                "graded": graded,
                "revised": revised,
                "revision_iterations": revision_iterations
            }

        except Exception as e:
            logger.error(f"Error in Self-RAG chat: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "sources": [],
                "tokens_used": 0,
                "retrieved": False,
                "graded": False,
                "revised": False
            }

    async def _generate_without_retrieval(
        self,
        message: str,
        history: List[Dict[str, str]],
        learning_mode: str,
        explain_depth: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate response without retrieval (for NO_RETRIEVE decisions)."""
        mode_config = get_mode_config(learning_mode)

        if system_prompt:
            final_system_prompt = system_prompt
        else:
            final_system_prompt = build_system_prompt(learning_mode, "", explain_depth)
            final_system_prompt += "\n\nNo external retrieval needed. Answer from your knowledge."

        messages = [{"role": "system", "content": final_system_prompt}]
        for msg in history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        messages.append({"role": "user", "content": message})

        chat_completion = self._groq_create(
            model=self.model,
            messages=messages,
            temperature=mode_config.get("temperature", 0.3),
            max_tokens=mode_config.get("max_tokens", 2000)
        )

        response = chat_completion.choices[0].message.content
        tokens_used = chat_completion.usage.total_tokens if chat_completion.usage else 0

        return {
            "response": response,
            "sources": [],
            "tokens_used": tokens_used,
            "retrieved": False,
            "graded": False,
            "revised": False
        }

    async def _generate_with_context(
        self,
        message: str,
        context: str,
        sources: List[Dict],
        learning_mode: str,
        explain_depth: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate response with fallback context."""
        mode_config = get_mode_config(learning_mode)

        if system_prompt:
            final_system_prompt = system_prompt
        else:
            final_system_prompt = build_system_prompt(learning_mode, context, explain_depth)

        messages = [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": message}
        ]

        chat_completion = self._groq_create(
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
            "tokens_used": tokens_used,
            "retrieved": False,
            "graded": False,
            "revised": False
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
        Stream chat response token by token using SSE-compatible format with Self-RAG.
        Yields dicts with "type" and "data" keys.
        """
        try:
            mode_config = get_mode_config(learning_mode)
            top_k = mode_config.get("top_k_chunks", 5)
            use_web = use_web_search or mode_config.get("use_web", False)

            # Self-RAG tracking
            retrieved = False
            graded = False

            # Step 1: Retrieval decision (if Self-RAG enabled)
            if self.enable_self_rag:
                yield {"type": "status", "data": {"message": "Evaluating if retrieval is needed..."}}
                needs_retrieval = await self._self_rag_retrieval_decision(message)
                if not needs_retrieval:
                    yield {"type": "status", "data": {"message": "Answering from knowledge..."}}
                    async for chunk in self._stream_without_retrieval(message, history, learning_mode, explain_depth, system_prompt):
                        yield chunk
                    return

            # Step 2: Retrieve documents
            yield {"type": "status", "data": {"message": "Retrieving relevant documents..."}}
            query_results = vector_store.query(topic_id, message, n_results=top_k)

            documents = query_results.get("documents", [])
            metadatas = query_results.get("metadatas", [])
            distances = query_results.get("distances", [])

            sources = []
            context = ""
            has_documents = bool(documents and documents[0]) if documents else False

            if not has_documents:
                use_web = True
                logger.info(f"No documents found for topic {topic_id}, using fallback")
                context = "No study material found for this topic. "
                curated_results = self._query_curated_base(message, top_k)
                if curated_results:
                    context += "Using curated content base:\n\n" + curated_results
                elif use_web:
                    yield {"type": "status", "data": {"message": "Searching the web..."}}
                    web_info = self._web_search(message)
                    context += "\n\n" + web_info
                else:
                    context += "Answering from general knowledge."

                async for chunk in self._stream_with_context(message, context, sources, learning_mode, explain_depth, system_prompt, history=history):
                    yield chunk
                return

            retrieved = True

            # Step 3: Grade documents (if Self-RAG enabled)
            if self.enable_self_rag:
                yield {"type": "status", "data": {"message": "Grading document relevance..."}}
                documents, metadatas = await self._self_rag_grade_documents(message, documents, metadatas)
                graded = True

            # Build sources and context
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

            yield {"type": "status", "data": {"message": "Generating response with citations..."}}

            # Stream the response with Self-RAG generation
            async for chunk in self._stream_with_context(
                message, context, sources, learning_mode, explain_depth, system_prompt,
                enable_citations=True, history=history
            ):
                yield chunk

            # Send sources after completion
            yield {"type": "sources", "data": {"sources": sources}}

            # Send self-rag metadata
            yield {"type": "metadata", "data": {
                "retrieved": retrieved,
                "graded": graded,
                "revised": False
            }}

        except Exception as e:
            logger.error(f"Error in streaming Self-RAG chat: {e}")
            yield {"type": "error", "data": {"error": str(e)}}

    async def _stream_without_retrieval(
        self,
        message: str,
        history: List[Dict[str, str]],
        learning_mode: str,
        explain_depth: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream response without retrieval."""
        mode_config = get_mode_config(learning_mode)

        if system_prompt:
            final_system_prompt = system_prompt
        else:
            final_system_prompt = build_system_prompt(learning_mode, "", explain_depth)
            final_system_prompt += "\n\nNo external retrieval needed. Answer from your knowledge."

        messages = [{"role": "system", "content": final_system_prompt}]
        for msg in (history or [])[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        messages.append({"role": "user", "content": message})

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

        yield {"type": "sources", "data": {"sources": []}}
        yield {"type": "done", "data": {
            "response": full_response,
            "tokens_used": int(len(full_response.split()) * 1.3)
        }}

    async def _stream_with_context(
        self,
        message: str,
        context: str,
        sources: List[Dict],
        learning_mode: str,
        explain_depth: Optional[str] = None,
        system_prompt: Optional[str] = None,
        enable_citations: bool = False,
        history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream response with context."""
        mode_config = get_mode_config(learning_mode)

        if system_prompt:
            final_system_prompt = system_prompt
        else:
            final_system_prompt = build_system_prompt(learning_mode, context, explain_depth)

        if enable_citations:
            final_system_prompt += """

IMPORTANT: Use citations in [Source: filename] format for all claims from documents."""

        messages = [{"role": "system", "content": final_system_prompt}]
        for msg in (history or [])[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        messages.append({"role": "user", "content": message})

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

        yield {"type": "done", "data": {
            "response": full_response,
            "tokens_used": int(len(full_response.split()) * 1.3)
        }}

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
            self._groq_create(
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
