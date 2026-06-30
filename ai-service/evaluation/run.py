"""
Self-RAG Evaluation for 3 Specific Areas:
1. Is Retrieval Needed? - Evaluate Self-RAG's retrieval decision
2. Relevance Grading - Evaluate document grading quality
3. Grounding Checks - Evaluate response grounding in sources

Usage:
    cd ai-service
    python -m evaluation.run
"""
import os
import sys
import json
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Local imports
from app.services.vector_store import vector_store
from app.core.rag_engine import rag_engine, SelfRAG

# Paths
EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.json"
RESOURCE_PATH = EVAL_DIR / "resource.pdf"
EVAL_TOPIC_ID = 999


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    """Load evaluation dataset from JSON."""
    with open(path, "r") as f:
        data = json.load(f)

    if isinstance(data, dict) and "samples" in data:
        return data["samples"]
    return data


def load_and_index_pdf(path: Path) -> List[Dict[str, Any]]:
    """Load PDF via the shared DocumentLoader and index into the vector store."""
    from app.core.document_loader import DocumentLoader

    print(f"   Loading PDF: {path}")

    MAX_CHUNKS = 50  # Cap to bound memory / embedding cost for the eval

    # Reuse the production PDF parsing + chunking instead of a bespoke fitz copy.
    chunks_data = DocumentLoader.load_pdf(str(path))[:MAX_CHUNKS]

    chunks = [c["text"] for c in chunks_data]
    metadatas = [{
        "source": str(path),
        "page": c["page"],
        "chunk_index": c["chunk_index"],
    } for c in chunks_data]

    # Clear existing data
    try:
        collection = vector_store.client.get_collection(name=f"topic_{EVAL_TOPIC_ID}")
        collection.delete(where={})
    except Exception:
        pass

    vector_store.add_documents(EVAL_TOPIC_ID, chunks, metadatas)
    print(f"   Indexed {len(chunks)} chunks")
    return chunks


async def evaluate_retrieval_needed(
    question: str,
    expected_retrieval_needed: bool
) -> Dict[str, Any]:
    """
    Area 1: Is Retrieval Needed?

    Evaluates whether Self-RAG correctly decides if retrieval is required.
    """
    # Call Self-RAG's retrieval decision
    needs_retrieval = await rag_engine._self_rag_retrieval_decision(question)

    # Compare with expected
    correct = needs_retrieval == expected_retrieval_needed

    return {
        "decision": "RETRIEVE" if needs_retrieval else "NO_RETRIEVE",
        "expected": "RETRIEVE" if expected_retrieval_needed else "NO_RETRIEVE",
        "correct": correct,
        "accuracy": 1.0 if correct else 0.0
    }


async def evaluate_relevance_grading(
    question: str,
    expected_relevant_count: int
) -> Dict[str, Any]:
    """
    Area 2: Relevance Grading

    Evaluates how well Self-RAG grades retrieved documents for relevance.
    """
    # Retrieve documents
    query_results = vector_store.query(EVAL_TOPIC_ID, question, n_results=5)
    documents = query_results.get("documents", [[]])[0]
    metadatas = query_results.get("metadatas", [[]])[0]

    if not documents or not documents[0]:
        return {
            "documents_retrieved": 0,
            "graded_relevant": 0,
            "expected": expected_relevant_count,
            "precision": 0.0,
            "note": "No documents retrieved"
        }

    # Run Self-RAG grading
    graded_docs, graded_metadatas = await rag_engine._self_rag_grade_documents(
        question, documents, metadatas
    )

    # Count documents graded as relevant (not filtered out)
    actual_relevant = len(graded_docs)

    # Calculate precision: how many of the retrieved were actually relevant
    precision = actual_relevant / len(documents) if documents else 0.0

    # Calculate recall: did we get the expected number of relevant docs
    recall = actual_relevant / expected_relevant_count if expected_relevant_count > 0 else 1.0

    return {
        "documents_retrieved": len(documents),
        "graded_relevant": actual_relevant,
        "expected": expected_relevant_count,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(2 * (precision * recall) / (precision + recall), 3) if (precision + recall) > 0 else 0.0
    }


async def evaluate_grounding(
    question: str,
    expected_citations: List[str]
) -> Dict[str, Any]:
    """
    Area 3: Grounding Checks

    Evaluates whether the response is grounded in retrieved sources and properly cited.
    """
    # Get response from RAG
    result = await rag_engine.chat(
        topic_id=EVAL_TOPIC_ID,
        message=question,
        history=[],
        learning_mode="MASTER_THIS"
    )

    response = result.get("response", "")
    sources = result.get("sources", [])

    # Check 1: Are there sources retrieved?
    has_sources = len(sources) > 0

    # Check 2: Does response contain citations?
    citation_pattern = r'\[Source:\s*([^\]]+)\]'
    citations_found = re.findall(citation_pattern, response, re.IGNORECASE)

    # Check 3: Are cited sources in the expected list?
    cited_sources_set = set(c.strip() for c in citations_found)
    expected_set = set(expected_citations)

    citations_match = bool(cited_sources_set & expected_set) if expected_citations else True
    all_expected_cited = expected_set.issubset(cited_sources_set) if expected_citations else True

    # Check 4: Run Self-RAG revision check
    query_results = vector_store.query(EVAL_TOPIC_ID, question, n_results=5)
    documents = query_results.get("documents", [[]])[0]
    metadatas = query_results.get("metadatas", [[]])[0]

    grounded = True
    if documents and documents[0]:
        # Run revision evaluation
        _, was_revised, _ = await rag_engine._self_rag_revision(
            question, response, documents, metadatas, max_iterations=1
        )
        # If it was revised, the original might not have been fully grounded
        grounded = not was_revised

    # Calculate overall grounding score
    grounding_score = 0.0
    if has_sources:
        grounding_score += 0.25
    if citations_found:
        grounding_score += 0.25
    if citations_match:
        grounding_score += 0.25
    if grounded:
        grounding_score += 0.25

    return {
        "response_length": len(response),
        "sources_retrieved": len(sources),
        "citations_found": citations_found,
        "citations_expected": expected_citations,
        "has_citations": bool(citations_found),
        "citations_match": citations_match,
        "all_expected_cited": all_expected_cited,
        "grounded": grounded,
        "grounding_score": grounding_score
    }


async def run_evaluation():
    """Run the 3-area Self-RAG evaluation."""

    print("=" * 60)
    print("Self-RAG Evaluation - 3 Areas")
    print("=" * 60)
    print("1. Is Retrieval Needed?")
    print("2. Relevance Grading")
    print("3. Grounding Checks")

    # 1. Load dataset
    print("\n[1/4] Loading evaluation dataset...")
    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        return

    dataset = load_dataset(DATASET_PATH)
    print(f"   Loaded {len(dataset)} evaluation samples")

    # 2. Load and index PDF
    print("\n[2/4] Loading and indexing PDF resource...")
    if not RESOURCE_PATH.exists():
        print(f"ERROR: Resource PDF not found at {RESOURCE_PATH}")
        return

    load_and_index_pdf(RESOURCE_PATH)

    # 3. Run evaluation for each sample
    print("\n[3/4] Running evaluation for each sample...")

    results = []

    for i, sample in enumerate(dataset):
        question = sample.get("question", "")
        ground_truth = sample.get("ground_truth", "")
        expected_retrieval = sample.get("retrieval_needed", True)
        expected_relevant = sample.get("expected_relevant_sources", 1)
        expected_citations = sample.get("expected_citations", [])

        print(f"\n   Sample {i+1}/{len(dataset)}")
        print(f"   Q: {question[:60]}...")

        # Area 1: Retrieval Decision
        retrieval_result = await evaluate_retrieval_needed(question, expected_retrieval)
        status = "PASS" if retrieval_result['correct'] else "FAIL"
        print(f"   [1] Retrieval: {retrieval_result['decision']} (expected: {retrieval_result['expected']}) - {status}")

        # Area 2: Relevance Grading
        relevance_result = await evaluate_relevance_grading(question, expected_relevant)
        print(f"   [2] Grading: {relevance_result['graded_relevant']}/{retrieval_result.get('documents_retrieved', 0)} relevant (precision: {relevance_result['precision']})")

        # Area 3: Grounding
        grounding_result = await evaluate_grounding(question, expected_citations)
        print(f"   [3] Grounding: score={grounding_result['grounding_score']}, citations={len(grounding_result['citations_found'])}")

        results.append({
            "question": question,
            "ground_truth": ground_truth,
            "retrieval": retrieval_result,
            "relevance": relevance_result,
            "grounding": grounding_result
        })

    # 4. Aggregate results
    print("\n[4/4] Computing aggregate metrics...")

    # Calculate aggregate scores
    retrieval_accuracy = sum(r["retrieval"]["accuracy"] for r in results) / len(results) if results else 0

    relevance_precisions = [r["relevance"]["precision"] for r in results if "precision" in r["relevance"]]
    avg_precision = sum(relevance_precisions) / len(relevance_precisions) if relevance_precisions else 0

    relevance_recalls = [r["relevance"]["recall"] for r in results if "recall" in r["relevance"]]
    avg_recall = sum(relevance_recalls) / len(relevance_recalls) if relevance_recalls else 0

    grounding_scores = [r["grounding"]["grounding_score"] for r in results]
    avg_grounding = sum(grounding_scores) / len(grounding_scores) if grounding_scores else 0

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 60)

    print(f"\nTotal Samples: {len(results)}")

    print(f"\n[1] IS RETRIEVAL NEEDED?")
    print(f"    Accuracy: {retrieval_accuracy:.1%}")
    correct = sum(r["retrieval"]["correct"] for r in results)
    print(f"    Correct: {correct}/{len(results)}")

    print(f"\n[2] RELEVANCE GRADING")
    print(f"    Avg Precision: {avg_precision:.1%}")
    print(f"    Avg Recall: {avg_recall:.1%}")
    print(f"    Avg F1: {2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0:.1%}")

    print(f"\n[3] GROUNDING CHECKS")
    print(f"    Avg Grounding Score: {avg_grounding:.1%}")
    with_citations = sum(1 for r in results if r["grounding"]["has_citations"])
    print(f"    Responses with Citations: {with_citations}/{len(results)}")

    # Overall score
    overall = (retrieval_accuracy + avg_precision + avg_grounding) / 3
    print(f"\nOVERALL SCORE: {overall:.1%}")

    # Save results
    output_path = EVAL_DIR / "results.json"
    output_data = {
        "summary": {
            "total_samples": len(results),
            "retrieval_accuracy": retrieval_accuracy,
            "relevance_precision": avg_precision,
            "relevance_recall": avg_recall,
            "grounding_score": avg_grounding,
            "overall_score": overall
        },
        "samples": results
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved to: {output_path}")

    return output_data


if __name__ == "__main__":
    asyncio.run(run_evaluation())