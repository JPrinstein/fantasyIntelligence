from pathlib import Path

def load_documents(directory="documents"):
    documents = []

    for file in Path("documents").glob("*.txt"):
        text = file.read_text(encoding="utf-8")

        documents.append({
            "text": text,
            "source": file.name
        })

    return documents