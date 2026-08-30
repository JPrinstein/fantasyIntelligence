from transformers import pipeline
from transformers.utils import logging
import torch

MODEL_NAME = "Qwen/Qwen3-1.7B"

generator = None

logging.set_verbosity_error()

def get_generator():
    global generator

    if generator is None:
        generator = pipeline("text-generation", model=MODEL_NAME)

    return generator

def generate_answer(question,context): #Will add more context/tools later on

    generator = get_generator()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a fantasy football assistant."
                "Answer using only the provided context."
                "If the context does not contain enough information, say so."
                "Give one concise answer and do not repeat yourself."
            )
        },
        {
            "role": "user",
            "content": f"""
                CONTEXT:
                {context}

                QUESTION:
                {question}
                """
        }
                ]

    output = generator(
        messages, 
        max_new_tokens=150,
        do_sample=True, #False = Picks single most likely token instead of our normal sampling
        temperature=.7,
        top_p=.8,
        top_k=20,
        return_full_text=False
    ) # Set do_sample back to true because it was repeating itself which is one of the most common issues with picking the top token.

    return output[0]["generated_text"]