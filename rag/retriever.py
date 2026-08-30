from rag.embeddings import embed_texts
from rag.vector_store import search_index

def retrieve(question, chunks, index, k=2):
    question_embedding = embed_texts([question])

    distances, indices = search_index(index, question_embedding, k)

    results = []

    for i, index_number in enumerate(indices[0]):
        results.append({
            "text": chunks[index_number]["text"],
            "source": chunks[index_number]["source"],
            "distance": distances[0][i]
        })

    return results