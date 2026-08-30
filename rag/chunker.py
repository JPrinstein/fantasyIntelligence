def chunk_text(text, chunk_size=500):
    words = text.split()

    chunks = []

    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))

    return chunks

def chunk_documents(documents, chunk_size=500):
    chunks = []

    for document in documents:
        document_chunks = chunk_text(document["text"], chunk_size)

        for chunk in document_chunks:
            chunks.append({
                "text": chunk,
                "source": document["source"]
            })

    return chunks