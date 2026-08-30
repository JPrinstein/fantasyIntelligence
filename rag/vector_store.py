import faiss

def build_index(embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    return index

def search_index(index, query_embedding, k=2):
    distances, indices = index.search(query_embedding, k)

    return distances, indices