def chunk_text(text, chunk_size=50, overlap=15):
    words = text.split()

    chunks = []

    step = chunk_size - overlap

    for i in range(0, len(words), step):
        chunk = words[i:i+chunk_size]
        if chunk:
            chunks.append(" ".join(chunk))

    return chunks

def chunk_documents(documents, chunk_size=50, overlap=15):
    chunks = []

    for document in documents:
        document_chunks = chunk_text(document["text"], chunk_size, overlap)

        source = document["source"]
        document_id = source.removesuffix(".txt")

        for chunk_id, chunk in enumerate(document_chunks):
            chunks.append({
                "text": chunk,
                "source": document["source"],
                "document_id": document_id,
                "chunk_id": chunk_id
            })

    return chunks