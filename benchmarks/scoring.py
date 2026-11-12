"""Metrics are strict and deliberately limited to what the cases establish."""
import json
import re
from collections import Counter


def parse_plan(raw):
    try:
        obj = json.loads(raw.strip())
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("tools"), list):
        return None
    for call in obj["tools"]:
        if not isinstance(call, dict) or not isinstance(call.get("tool"), str) or not isinstance(call.get("args"), dict):
            return None
    return obj


def score_case(case, output):
    if case["kind"] == "planner":
        plan = parse_plan(output)
        if plan is None:
            return {"passed": False, "json_valid": False, "detail": "Invalid planner JSON/schema"}
        calls = plan["tools"]
        names_correct = Counter(call["tool"] for call in calls) == Counter(case["expected_tools"])
        arguments_correct = True
        for name, expected_calls in case.get("expected_args", {}).items():
            actual = [call["args"] for call in calls if call["tool"] == name]
            # Exact equality intentionally catches invented optional arguments.
            arguments_correct &= Counter(json.dumps(x, sort_keys=True) for x in actual) == Counter(
                json.dumps(x, sort_keys=True) for x in expected_calls
            )
        return {"passed": bool(names_correct and arguments_correct), "json_valid": True,
                "tools_correct": names_correct, "arguments_correct": bool(arguments_correct)}

    lowered = output.casefold()
    # "2,549" and "2549" represent the same number. Avoid a false failure
    # caused only by thousands-separator formatting.
    canonical = re.sub(r"(?<=\d),(?=\d)", "", lowered)
    number_words = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
                    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten"}

    def contains_expected(value):
        normalized = re.sub(r"(?<=\d),(?=\d)", "", value.casefold())
        if normalized.isdigit():
            return re.search(rf"(?<!\d){re.escape(normalized)}(?!\d)", canonical) is not None or (
                normalized in number_words and re.search(rf"\b{number_words[normalized]}\b", lowered) is not None)
        return normalized in canonical

    missing = [s for s in case.get("must_contain", []) if not contains_expected(s)]
    any_options = case.get("must_contain_any", [])
    missing_any = bool(any_options) and not any(s.casefold() in lowered for s in any_options)
    forbidden = [s for s in case.get("forbidden_phrases", []) if re.search(re.escape(s.casefold()), lowered)]
    return {"passed": not missing and not forbidden and not missing_any,
            "missing": missing, "missing_any": missing_any, "forbidden": forbidden,
            "note": "String checks only; does not prove numerical factuality"}
