import faiss

def build_index(embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    return index

def search_index(index, query_embedding, k=2):
    scores, indices = index.search(query_embedding, k)

    return scores, indices

def save_index(index,path):
    faiss.write_index(index, path)

def load_index(path):
    return faiss.read_index(path)