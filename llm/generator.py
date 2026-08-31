from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.utils import logging

MODEL_NAME = "Qwen/Qwen3-1.7B"

model = None
tokenizer = None

logging.set_verbosity_error()

def get_generator():
    global model
    global tokenizer

    if model is None or tokenizer is None:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME,            #CausalLM = previous tokens -> predict next token
                                                     torch_dtype="auto",    #torch_dtype and device_map helps automatically place the model based on my hardware
                                                     ) 

    return model, tokenizer

def generate_answer(question,context, thinking=False): #Will add more context/tools later on

    model, tokenizer = get_generator()

    messages = [
        {
            "role": "system",
           "content": (
                "You are a fantasy football assistant. "
                "Answer specifically about fantasy football value, not real-world football importance. "
                "Use only the provided evidence for factual claims. "
                "Do not assume league scoring or roster settings that are not provided. "
                "If a question compares multiple positions, players, or concepts, "
                "the evidence must contain relevant information about each one. "
                "If there is not enough evidence to answer confidently, say so. "
                "Do not invent meanings for fantasy football terms or abbreviations. "
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

    text = tokenizer.apply_chat_template(
        messages,
        tokenize = False,
        add_generation_prompt = True,
        enable_thinking = thinking
    )

    inputs = tokenizer(
        text,
        return_tensors="pt"
    ).to(model.device)

    tokens = 150
    if thinking:
        tokens = 500

    outputs = model.generate(
        **inputs,
        max_new_tokens=tokens,
        do_sample=True,
        temperature=0.6,
        top_p=0.95,
        top_k=20
    )

    input_length = inputs["input_ids"].shape[1]
    generated_tokens = outputs[0][input_length:] #Removes the original prompt from the output

    answer = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    )

    return answer.strip()