from rag.vector_store import load_index
from rag.storage import load_chunks
from rag.retriever import retrieve
from rag.reranker import rerank_results


TEST_CASES = [
    # Original baseline
    ("What does PPR mean?", "fantasy_scoring.txt"),
    ("Why are rushing quarterbacks valuable?", "quarterbacks.txt"),
    ("Why are receptions valuable for running backs?", "running_backs.txt"),
    ("How many points is a rushing touchdown worth?", "fantasy_scoring.txt"),

    # Different wording
    ("Explain points per reception scoring.", "fantasy_scoring.txt"),
    ("How does running the ball help a fantasy QB?", "quarterbacks.txt"),
    ("Why is receiving workload important for an RB?", "running_backs.txt"),

    # More complex questions
    ("What makes a quarterback valuable besides passing?", "quarterbacks.txt"),
    ("How do goal-line opportunities affect running backs?", "running_backs.txt"),
    ("How do league settings affect fantasy scoring?", "fantasy_scoring.txt"),

    # Position-specific context
    ("Which factors influence a quarterback's fantasy production?", "quarterbacks.txt"),
    ("Why does a running back's workload matter?", "running_backs.txt"),
]


def main():
    chunks = load_chunks("rag_data/chunks.json")
    index = load_index("rag_data/index.faiss")

    top1_correct = 0
    recall3_correct = 0
    reciprocal_rank_total = 0

    for question, expected_source in TEST_CASES:
        results = retrieve(question, chunks, index, k=6)
        results = rerank_results(question, results, max_results=3)

        sources = [result["source"] for result in results]

        print(f"\nQuestion: {question}")
        print(f"Expected: {expected_source}")
        print(f"Retrieved: {sources}")

        if sources and sources[0] == expected_source:
            top1_correct += 1

        if expected_source in sources:
            recall3_correct += 1

            rank = sources.index(expected_source) + 1
            reciprocal_rank_total += 1 / rank

    total = len(TEST_CASES)

    print("\n=== RETRIEVAL EVALUATION ===")
    print(f"Top-1 Accuracy: {top1_correct / total:.2%}")
    print(f"Recall@3: {recall3_correct / total:.2%}")
    print(f"MRR: {reciprocal_rank_total / total:.3f}")


if __name__ == "__main__":
    main()