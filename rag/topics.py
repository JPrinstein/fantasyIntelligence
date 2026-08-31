import re

TOPIC_ALIASES = {
    "quarterbacks": [
        "quarterback",
        "quarterbacks",
        "qb",
        "qbs"
    ],
    "running_backs": [
        "running back",
        "running backs",
        "rb",
        "rbs"
    ],
    "wide_receivers": [
        "wide receiver",
        "wide receivers",
        "wr",
        "wrs"
    ]
}

def get_question_topics(question):
    question = question.lower()
    topics = []

    for topic, aliases in TOPIC_ALIASES.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", question): #REGEXXXXX
                topics.append(topic)
                break

    return topics