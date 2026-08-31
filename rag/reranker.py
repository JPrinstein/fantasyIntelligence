## This will help rerank our documents so we're getting the documents that actually answer our question.
# Was having a major problem with the LLM pulling data from the RB file for QBs and giving nonsense about PPR for QBs

from sentence_transformers import CrossEncoder

RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"

reranker_model = None

def get_reranker(): #Same "caching" as with QWEN loading
    global reranker_model

    if reranker_model is None:
        reranker_model = CrossEncoder(RERANKER_MODEL_NAME)

    return reranker_model

def rerank_results(question, results, max_results = 3):
    if not results: #Since we may not get any documents with context to start
        return []

    model = get_reranker()

    pairs = [(question, result["text"]) for result in results] #The cross-encoder is going to compare the question to each text

    scores = model.predict(pairs) #Actually running the pairs through the cross-encoder, scores will vary so instead of a threshold we will simply take the top max_results(currently 3)

    reranked = []

    for result, score in zip(results, scores): #Makes a tuple out of each results and scores and then maps to result and score
        reranked.append({
            **result,
            "rerank_score": float(score)
        })

    reranked.sort(
        key=lambda result: result["rerank_score"],
        reverse=True
    )

    return reranked[:max_results]