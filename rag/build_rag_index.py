from pathlib import Path

from rag.loader import load_documents
from rag.chunker import chunk_documents
from rag.embeddings import embed_texts
from rag.vector_store import build_index, save_index
from rag.storage import save_chunks

OUTPUT_DIRECTORY = Path("rag_data")

def main():
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)

    documents = load_documents()

    chunks = chunk_documents(documents, chunk_size=50,overlap=15)

    texts = [chunk["text"] for chunk in chunks]

    embeddings = embed_texts(texts)

    index = build_index(embeddings)

    save_index(index, str(OUTPUT_DIRECTORY / "index.faiss"))

    save_chunks(chunks, OUTPUT_DIRECTORY / "chunks.json")

    print(f"Saved {len(chunks)} chunks.")
    print(f"Index: {OUTPUT_DIRECTORY / 'index.faiss'}")
    print(f"Chunks: {OUTPUT_DIRECTORY / 'chunks.json'}")

if __name__ == "__main__":
    main()