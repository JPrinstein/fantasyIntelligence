from rag.vector_store import load_index
from rag.storage import load_chunks

from league.loader import load_league

from llm.generator import generate_answer
from llm.runtime import backend, get_generator, get_last_generation_metrics

from agent.planner import create_plan, enforce_required_tools, AVAILABLE_TOOLS
from agent.validator import validate_plan
from agent.executor import execute_plan
from agent.evidence import build_evidence

import time

def print_generation_metrics():
    if backend() != "gguf":
        return

    metrics = get_last_generation_metrics()

    tokens = metrics.get("tokens", 0)
    tps = metrics.get("tokens_per_second")

    print(f"Generated tokens: {tokens}")

    if tps is not None:
        print(f"Generation speed: {tps:.2f} tok/s")
    else:
        print("Generation speed: unavailable")

chunks = load_chunks("rag_data/chunks.json")
index = load_index("rag_data/index.faiss")
league = load_league()

print("Inference backend:", backend())
if backend() == "transformers":
    model, tokenizer = get_generator()
    print("Model device:", next(model.parameters()).device)
    print("Model dtype:", next(model.parameters()).dtype)

while True:
    question = input("Ask a fantasy football question(type 'quit' or 'exit' to quit): ")

    if question.lower().strip() in {"quit","exit"}:
        break

    start = time.perf_counter()

    plan = create_plan(question)

    end = time.perf_counter()

    print(f"\nPlanner time: {end-start:.2f}s")

    print_generation_metrics()

    if plan.get("error"):
        print("\nPLAN ERROR:", plan["error"])
        continue

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

    start = time.perf_counter()

    answer = generate_answer(
        question,
        rag_context = evidence["rag_context"],
        league_context = evidence["league_context"],
        tool_context=evidence["tool_context"]
    )

    end = time.perf_counter()

    print(f"\nAnswer generation time: {end - start:.2f}s")

    print_generation_metrics()

    print("\nANSWER:")
    print(answer)