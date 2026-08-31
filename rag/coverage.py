## ONLY WORKING BECAUSE OUR DOCUMENTS SYSTEM IS SO SIMPLE, WILL HAVE TO UPDATE LATER ON!!!!

TOPIC_ALIASES = {
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
    ],
    "quarterbacks": [
        "quarterback",
        "quarterbacks",
        "qb",
        "qbs"
    ],
}

def get_question_topics(question):
    question = question.lower()
    topics = []

    for topic, aliases in TOPIC_ALIASES.items():
        for alias in aliases:
            if alias in question:
                topics.append(topic)
                break

    return topics

def check_coverage(question, results):
    required_topics = get_question_topics(question)

    if not required_topics:
        return True, []

    retrieved_topics = set()

    for result in results:
        source = result["source"]
        if source.endswith(".txt"):
            source = source[:-4]

        retrieved_topics.add(source)

    missing_topics = [topic for topic in required_topics if topic not in retrieved_topics]

    coverage_complete = (len(missing_topics) == 0)

    return coverage_complete, missing_topics