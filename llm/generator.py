from transformers import pipeline
import torch

MODEL_NAME = "Qwen/Qwen3-1.7B"

generator = None

def get_generator():
    global generator

    if generator is None:
        generator = pipeline("text-generation", model=MODEL_NAME)

    return generator

def generate_answer(question,context): #Will add more context/tools later on

    generator = get_generator()

    prompt = f"""
        You are a fantasy football assistant.

        Answer the question using only the provided context. 

        If the context does not contain enough information,
        say that you do not have enough information.

        CONTEXT:
        {context}

        QUESTION:
        {question}

        ANSWER:
        """

    output = generator(
        prompt, 
        max_new_tokens=200,
        do_sample=True, #False = Picks single most likely token instead of our normal sampling
        temperature=.7,
        top_p=.8,
        top_k=20,
        return_full_text=False
    ) # Set do_sample back to true because it was repeating itself which is one of the most common issues with picking the top token.

    return output[0]["generated_text"]