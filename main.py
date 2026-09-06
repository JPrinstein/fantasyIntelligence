from rag.vector_store import load_index
from rag.storage import load_chunks

from league.loader import load_league

from llm.generator import generate_answer, get_generator

from agent.planner import create_plan, enforce_required_tools, AVAILABLE_TOOLS
from agent.validator import validate_plan
from agent.executor import execute_plan
from agent.evidence import build_evidence

chunks = load_chunks("rag_data/chunks.json")
index = load_index("rag_data/index.faiss")
league = load_league()

get_generator()

while True:
    question = input("Ask a fantasy football question(type 'quit' or 'exit' to quit): ")

    if question.lower().strip() in {"quit","exit"}:
        break

    plan = create_plan("question")

    plan = enforce_required_tools(
        question,
        plan
    )

    validation = validate_plan(plan, AVAILABLE_TOOLS)

    print("\nPLAN:")
    print(plan)

    if not validation["valid"]:
        print("\nPLAN ERROR:")
        print(validation["errors"])
        continue

    execution_result = execute_plan(
        plan,
        chunks,
        index,
        league
    )

    evidence = build_evidence(execution_result)

    answer = generate_answer(
        question,
        rag_context = evidence["rag_context"],
        league_context = evidence["league_context"]
    )

    print("\nANSWER:")
    print(answer)