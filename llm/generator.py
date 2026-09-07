from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.utils import logging

MODEL_NAME = "Qwen/Qwen3-4B"

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
                                                     ).to("cuda")

    return model, tokenizer

def generate_answer(question, rag_context, league_context="", tool_context="",thinking=False): #Will add more context/tools later on

    model, tokenizer = get_generator()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a fantasy football assistant. "
                "Answer specifically about fantasy football value, not real-world football importance. "

                "Use only the provided evidence for factual claims. "
                "The evidence may include RAG context, league context, and tool context. "

                "Tool context contains factual structured data returned by trusted tools, "
                "such as player statistics, matchup data, injury data, or projections. "
                "Treat tool context as authoritative for those factual values. "
                "Do not invent, estimate, or alter statistics that are not present in the provided evidence. "

                "Use league context as the authoritative source for league-specific "
                "scoring and roster settings. General fantasy football information "
                "from RAG must not override explicit league settings. "

                "Use RAG context for general fantasy football concepts, strategy, terminology, "
                "and explanations when that information is provided. "

                "Do not assume league scoring or roster settings that are not provided. "
                "Do not invent meanings for fantasy football terms or abbreviations. "

                "If a question compares multiple positions, players, or concepts, "
                "the evidence must contain relevant information about each one. "

                "If there is not enough evidence to answer confidently, say so. "

                "If the question asks about the user's specific league but no league context "
                "is provided, do not make league-specific claims. State that the available "
                "evidence is insufficient to determine how the user's league changes the answer. "

                "When numerical statistics are provided in tool context, use those exact values "
                "and do not recalculate them unless the question explicitly requires a calculation. "

                "Do not infer trends, consistency, efficiency, improvement, decline, or other "
                "performance patterns unless the provided evidence directly supports that conclusion. "

                "When tool context provides aggregate statistics, describe only those statistics. "
                "Do not infer game-to-game trends or consistency from season totals alone. "

                "Give one concise answer and do not repeat yourself."
            )
        },
        {
            "role": "user",
            "content": f"""
                RAG EVIDENCE:
                {rag_context}

                LEAGUE CONTEXT:
                {league_context}

                TOOL CONTEXT:
                {tool_context}

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
        do_sample=False,
        #temperature=0.6,
        #top_p=0.95,
        #top_k=20
    )

    input_length = inputs["input_ids"].shape[1]
    generated_tokens = outputs[0][input_length:] #Removes the original prompt from the output

    answer = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    )

    return answer.strip()