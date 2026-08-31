from rag.embeddings import embed_texts
from rag.vector_store import search_index

def retrieve(question, chunks, index, k=5, minimum_score=.5): #Max distance will be ~1.5
    question_embedding = embed_texts([question])

    scores, indices = search_index(index, question_embedding, k)

    results = []

    for i, index_number in enumerate(indices[0]):
        
        if scores[0][i] >= minimum_score:
            results.append({
                "text": chunks[index_number]["text"],
                "source": chunks[index_number]["source"],
                "score": scores[0][i]
            })

    return results