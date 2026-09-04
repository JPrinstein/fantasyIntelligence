from rag.retriever import retrieve
from rag.reranker import rerank_results
from rag.coverage import check_coverage


TOOL_NAME = "rag_search"

TOOL_DESCRIPTION = (
    "Search the fantasy football knowledge base for general "
    "fantasy football rules, concepts, strategy, and positional information."
)

def rag_search(question, chunks, index):
    results = retrieve(question, chunks, index, k=10)

    if not results:
        return {
            "success": False,
            "content": "",
            "sources": []
        }

    coverage_complete, missing_topics = check_coverage(question, results)

    if not coverage_complete:
        return {
            "success": False,
            "content": "",
            "sources": [],
            "missing_topics": missing_topics
        }

    results = rerank_results(question, results, max_results=3)

    print("\n\nRetrieved Content")
    for result in results:
        print(f"\nSource: {result['source']}")
        print(f"Similarity: {result['score']}")
        print(f"Rerank Score: {result['rerank_score']}")
        print(result["text"])

    content = "\n\n".join(result["text"] for result in results)
    sources = [result["source"] for result in results]

    return {
        "success": True,
        "content": content,
        "sources": sources
    }