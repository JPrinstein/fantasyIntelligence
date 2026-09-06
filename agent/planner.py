import json

from llm.generator import get_generator
from tools.rag_tool import TOOL_NAME as RAG_TOOL_NAME
from tools.rag_tool import TOOL_DESCRIPTION as RAG_TOOL_DESCRIPTION
from tools.league_tool import TOOL_NAME as LEAGUE_TOOL_NAME
from tools.league_tool import TOOL_DESCRIPTION as LEAGUE_TOOL_DESCRIPTION
from agent.validator import validate_plan

AVAILABLE_TOOLS = {
    LEAGUE_TOOL_NAME:{
            "description": RAG_TOOL_DESCRIPTION,
            "arguments":{}
        },

    RAG_TOOL_NAME:{
        "description": RAG_TOOL_DESCRIPTION,
        "arguments": {
            "query": "The search query to use for the knowledge base."
        }
    }
}

def build_tools_prompt():
    lines = []

    for tool_name, tool_info in AVAILABLE_TOOLS.items():

        lines.append(f"Tool: {tool_name}")
        lines.append(f"Description: {tool_info["description"]}")

        if tool_info["arguments"]:
            lines.append("Arguments:")

            for argument, description in tool_info["arguments"].items():
                lines.append(f"{argument}: {description}")

        else:
            lines.append("Arguments: none")

        lines.append("")

    return "\n".join(lines)

def create_plan(question):
    model, tokenizer = get_generator()

    tools_prompt = build_tools_prompt()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a tool planner for a fantasy football assistant. "
                "Your only job is to choose which available tools are needed. "
                "Do not answer the fantasy football question yourself. "

                "TOOL RULES: "

                "Use rag_search ONLY for general fantasy football knowledge, strategy, "
                "terminology, concepts, or position information. "

                "Any question containing phrases such as 'my league', 'in my league', "
                "'this league', 'our league', 'my scoring', or 'my roster' MUST use "
                "league_context. This rule is mandatory even if rag_search is also needed. "

                "If the question can be answered entirely from league settings, use "
                "league_context and DO NOT use rag_search. "

                "If the question asks for general fantasy football reasoning AND refers "
                "to the user's specific league, use BOTH rag_search and league_context. "

                "If the question asks WHY or HOW a fantasy concept, player type, or position is valuable, "
                "use rag_search for the general explanation. "
                "If the question also refers to the user's league, use BOTH rag_search and league_context. "

                "EXAMPLES: "
                "'What does PPR mean?' -> rag_search only. "
                "'Is this a PPR league?' -> league_context only. "
                "'How many points is a passing touchdown in my league?' -> league_context only. "
                "'Why are rushing quarterbacks valuable?' -> rag_search only. "
                "'Why are rushing quarterbacks valuable in my league?' -> rag_search and league_context. "

                "Return only valid JSON. Do not include markdown, commentary, or explanation."
            )
        },
        {
            "role": "user",
            "content": f"""
            AVAILABLE TOOLS:

            {tools_prompt}

            QUESTION:
            {question}

            Return JSON in exactly this structure:

            {{
                "tools": [
                    {{
                        "tool": "tool_name",
                        "args": {{}}
                    }}
                ]
            }}
            """
        }
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize = False,
        add_generation_prompt = True,
        enable_thinking = False
    )

    inputs = tokenizer(
        text,
        return_tensors="pt"
    ).to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=200,
        do_sample=False
    )

    input_length = inputs["input_ids"].shape[1]

    generated_tokens = outputs[0][input_length:] #Input length got the length of our input and then cut that off so we only get the new stuff

    response = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    ).strip()

    print("\nRAW PLANNER RESPONSE:")
    print(repr(response))

    try:
        plan = json.loads(response)
    except json.JSONDecodeError:
        return{
            "tools": [],
            "error": "Planner returned invalid JSON",
            "raw_response": response
        }

    return plan

def enforce_required_tools(question,plan):
    question_lower= question.lower()

    selected_tools = {tool_call["tool"] for tool_call in plan.get("tools", [])
                      if isinstance(tool_call, dict) and "tool" in tool_call}

    league_phrases = [
        "my league",
        "in my league",
        "this league",
        "our league",
        "my scoring",
        "my roster"
    ]

    rag_phrases = [
        "why",
        "how",
        "valuable",
        "value",
        "important"
    ]

    needs_league_context = any(phrase in question_lower for phrase in league_phrases)
    needs_rag_context = any(phrase in question_lower for phrase in rag_phrases)

    if needs_league_context and "league_context" not in selected_tools:
        plan["tools"].append({
            "tool": "league_context",
            "args": {}
        })

    if needs_rag_context and "rag_search" not in selected_tools:
            plan["tools"].append({
                "tool": "rag_search",
                "args": {
                    "query": question
                }
            })

    return plan

if __name__ == "__main__":
    test_plans = [
        "hello",

        {},

        {
            "tools": "rag_search"
        },

        {
            "tools": [
                "hello"
            ]
        },

        {
            "tools": [
                {
                    "args": {}
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "fake_tool",
                    "args": {}
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "rag_search",
                    "args": {}
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "league_context",
                    "args": {
                        "banana": 123
                    }
                }
            ]
        },

        {
            "tools": [
                {
                    "tool": "rag_search",
                    "args": {
                        "query": "What does PPR mean?"
                    }
                }
            ]
        }
    ]


    for plan in test_plans:
        print(plan)
        print(validate_plan(plan, AVAILABLE_TOOLS))
        print()

    