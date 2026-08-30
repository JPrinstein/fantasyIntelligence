from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss

## Chunking our text so we can embed smaller pieces at a time
def chunk_text(text, chunk_size=500):
    words = text.split()

    chunks = []

    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))

    return chunks

## Create a documents dict for each file we have

documents = []

for file in Path("documents").glob("*.txt"):
    text = file.read_text(encoding="utf-8")

    documents.append({
        "text": text,
        "source": file.name
    })

#print(documents)

## Re-creating our dict for our chunked documents

chunks = []

for document in documents:
    document_chunks = chunk_text(document["text"])

    for chunk in document_chunks:
        chunks.append({
            "text": chunk,
            "source": document["source"]
        })

#print(chunks)

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

texts = [chunk["text"] for chunk in chunks]

## Encoding all of our chunked texts - 384-dimentional vector
embeddings = embedding_model.encode(texts)


## Creating the FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)


## Preparing our test question
question = "Why is receiving valuable for running backs?"
question_embedding = embedding_model.encode([question])

distances, indices = index.search(question_embedding, k=3)

print(f"Loaded {len(documents)} documents")
print(f"Created {len(chunks)} chunks")
print(f"Embedding dimensions: {embeddings.shape[1]}")

print(f"\nRetrieved {len(indices[0])} results\n")

results = []
for index_number in indices[0]:
    results.append(chunks[index_number])

for result in results:
    print(result["source"])
    print(result["text"])


## Better testing output with distance
"""for i, index_number in enumerate(indices[0]):
    print("Distance:", distances[0][i])
    print("Source:", chunks[index_number]["source"])
    print("Text:", chunks[index_number]["text"])
    print()"""