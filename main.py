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
from tools.rag_tool import rag_search
from tools.league_tool import get_league_context
from agent.planner import build_tools_prompt

chunks = load_chunks("rag_data/chunks.json")
index = load_index("rag_data/index.faiss")

league = load_league()
league_context = build_league_context(league)

get_generator()

rag_result = rag_search(
    "Why are rushing quarterbacks valuable?",
    chunks,
    index
)

print(rag_result)

league_result = get_league_context(league)

print(league_result)

print(build_tools_prompt())

"""
while True:
    question = input("\n\nAsk a fantasy football question(type 'quit' to exit): ") #Gets our question from the user

    if question.lower().strip() == "quit":
        break

    rag_context = rag_search(question, chunks, index)

    print("\n\nANSWER:\n\n")

    answer = generate_answer(question,rag_context=rag_context, league_context=league_context) #ANSWER!!!

    print(answer)
"""