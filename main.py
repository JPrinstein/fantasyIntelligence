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

chunks = load_chunks("rag_data/chunks.json")
index = load_index("rag_data/index.faiss")

get_generator()


while True:
    question = input("\n\nAsk a fantasy football question(type 'quit' to exit): ") #Gets our question from the user

    if question.lower().strip() == "quit":
        break

    results = retrieve(question, chunks, index, k=10) #RAG results

    if not results:
        print("I couldn't find relevant information in the available documents.") #Important because RAG is our only way of getting information. Once tools are added and more context etc. then this will be changed
        continue

    coverage_complete, missing_topics = check_coverage(question, results)

    if not coverage_complete:
        print("\nI don't have enough information to fully answer that question.")
        print(f"Missing information about: {', '.join(missing_topics)}\n")
        continue

    results = rerank_results(question, results, max_results=3)

    print("\n\nRetrieved Content")
    for result in results:
        print(f"\nSource: {result['source']}")
        print(f"Similarity: {result['score']}")
        print(f"Rerank Score: {result['rerank_score']}")
        print(result["text"])

    print("\n\nANSWER:\n\n")

    context = "\n\n".join(result["text"] for result in results) #Combines our results into our context


    answer = generate_answer(question,context) #ANSWER!!!

    print(answer)