from rag.loader import load_documents
from rag.chunker import chunk_documents
from rag.embeddings import embed_texts
from rag.vector_store import build_index
from rag.retriever import retrieve
from llm.generator import generate_answer, get_generator
from rag.coverage import check_coverage
from rag.reranker import rerank_results
from rag.vector_store import load_index
from rag.storage import load_chunks
from league.loader import load_league
from league.context import build_league_context

chunks = load_chunks("rag_data/chunks.json")
index = load_index("rag_data/index.faiss")

league = load_league()
league_context = build_league_context(league)

get_generator()


while True:
    question = input("\n\nAsk a fantasy football question(type 'quit' to exit): ") #Gets our question from the user

    if question.lower().strip() == "quit":
        break

    results = retrieve(question, chunks, index, k=10) #RAG results

    rag_context = ""

    if results:
        coverage_complete, missing_topics = check_coverage(question, results)

        if coverage_complete:
            results = rerank_results(question, results, max_results=3)

            rag_context = "\n\n".join(result["text"] for result in results)

            print("\n\nRetrieved Content")
            for result in results:
                print(f"\nSource: {result['source']}")
                print(f"Similarity: {result['score']}")
                print(f"Rerank Score: {result['rerank_score']}")
                print(result["text"])

    else:
        rag_context = ""

    print("\n\nANSWER:\n\n")

    answer = generate_answer(question,rag_context=rag_context, league_context=league_context) #ANSWER!!!

    print(answer)