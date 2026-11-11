def chunk_text(text, chunk_size=50, overlap=15):
    paragraphs = [
        paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()
    ]

    chunks = []
    current_paragraphs = []
    current_word_count = 0

    for paragraph in paragraphs:
        paragraph_word_count = len(paragraph.split())

        #If adding this paragraph exceeds our target, save the current chunk first and put this in the next chunk
        if(
            current_paragraphs and current_word_count + paragraph_word_count > chunk_size
        ):
            chunks.append(" ".join(current_paragraphs))

            current_paragraphs = []
            current_word_count = 0

        current_paragraphs.append(paragraph)
        current_word_count += paragraph_word_count

    if current_paragraphs:
        chunks.append(" ".join(current_paragraphs))

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