from transformers import pipeline

#Note - will have to experiment with which model is best, but will use qwen 1.5B for now
generator = pipeline("text-generation", model="Qwen/Qwen2.5-1.5B-Instruct")

def generate_answer(question,context): #Will add more context/tools later on
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
        max_new_tokens=500,
        do_sample=False #Picks single most likely token instead of our normal sampling
        )