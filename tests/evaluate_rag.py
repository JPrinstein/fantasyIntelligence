import json
from pathlib import Path

from rag.loader import load_documents
from rag.chunker import chunk_documents
from rag.embeddings import embed_texts
from rag.vector_store import build_index
from rag.retriever import retrieve
from rag.coverage import check_coverage
from rag.reranker import rerank_results
from rag.vector_store import load_index
from rag.storage import load_chunks

TEST_FILE = Path("tests/rag_questions.json")

def load_tests():
    with TEST_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)

def can_answer(question, chunks, index):
    results = retrieve(question,chunks,index,k=10) #Retrieving our documents

    if not results:
        return False

    coverage_complete, missing_topics = check_coverage(question, results)

    if not coverage_complete:
        return False

    results = rerank_results(question, results, max_results=3)

    return len(results) > 0 #Meaning we CAN answer because we have documents(currently our only way of getting info)

def main():
    chunks = load_chunks("rag_data/chunks.json")
    index = load_index("rag_data/index.faiss")  

    tests = load_tests()

    passed = 0

    for test in tests:
        question = test["question"]
        expected = test["should_answer"]

        actual = can_answer(question,chunks,index)

        if actual == expected:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"

        print(f"{status}: {question}")

        if actual != expected:
            print(f"Expected: {expected}")
            print(f"Actuual: {actual}")

    print(f"\n{passed}/{len(tests)} tests passed")

if __name__ == "__main__":
    main()