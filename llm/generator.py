from transformers import pipeline

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
git
        ANSWER:
        """

    output = generator(
        prompt, 
        max_new_tokens=500,
        do_sample=False, #Picks single most likely token instead of our normal sampling
        return_full_text=False
        )

    return output[0]["generated_text"]