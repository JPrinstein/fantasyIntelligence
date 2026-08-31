## This will help rerank our documents so we're getting the documents that actually answer our question.
# Was having a major problem with the LLM pulling data from the RB file for QBs and giving nonsense about PPR for QBs

# Will have to rework this majorly once it is not painfully simple, like the coverage aliases.

from rag.topics import get_question_topics

def rerank_results(question, results, max_results=3):
    question_topics = get_question_topics(question)

    reranked = []

    for result in results:
        rerank_score = result["score"]

        source = result["source"]

        if source.endswith(".txt"):
            source_topic = source[:-4]
        else:
            source_topic = source

        if question_topics:
            if source_topic in question_topics:
                rerank_score += .25
            else:
                rerank_score -= .25

        reranked.append({
            **result,
            "rerank_score": rerank_score
        })

    reranked.sort(
        key=lambda result: result["rerank_score"],
        reverse=True
    )

    return reranked[:max_results]
