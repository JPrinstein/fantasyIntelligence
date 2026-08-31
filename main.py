from rag.loader import load_documents
from rag.chunker import chunk_documents
from rag.embeddings import embed_texts
from rag.vector_store import build_index
from rag.retriever import retrieve
from llm.generator import generate_answer, get_generator

documents = load_documents() #Loading our documents, currently from the documents folder

chunks = chunk_documents(documents) #Chunking our documents, currently set to 500 words per

texts = [chunk["text"] for chunk in chunks] #Gets the text fo reach chunk(since each chunk) also has the sources

embeddings = embed_texts(texts) #Embeds each text

index = build_index(embeddings) #builds our FAISS index

get_generator()


while True:
    question = input("\n\nAsk a fantasy football question(type 'quit' to exit): ") #Gets our question from the user

    if question.lower().strip() == "quit":
        break

    results = retrieve(question, chunks, index, k=2) #RAG results(currently set to 2 documents(k))

    print("\n\nRetrieved Content")
    for result in results:
        print(f"\nSource: {result['source']}")
        print(f"Distance: {result['distance']}")
        print(result["text"])

    print("\n\nANSWER:\n\n")

    context = "\n\n".join(result["text"] for result in results) #Combines our results into our context


    answer = generate_answer(question,context) #ANSWER!!!

    print(answer)