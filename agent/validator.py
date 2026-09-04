def validate_plan(plan, available_tools):
    errors = []

    if not isinstance(plan, dict):
        return {
            "valid": False,
            "errors": ["Plan is not a dictionary."]
        }

    if "tools" not in plan:
        return {
            "valid": False,
            "errors": ['Plan is missing the "tools" key.']
        }

    tools = plan["tools"]

    if not isinstance(tools, list):
        return {
            "valid": False,
            "errors": ['plan["tools"] is not a list.']
        }

    for index, tool_call in enumerate(tools):

        if not isinstance(tool_call, dict):
            errors.append(
                f"Tool call {index} is not a dictionary."
            )
            continue

        if "tool" not in tool_call:
            errors.append(
                f'Tool call {index} is missing the "tool" key.'
            )
            continue

        tool_name = tool_call["tool"]

        if not isinstance(tool_name, str):
            errors.append(
                f'Tool call {index} has an invalid "tool" value.'
            )
            continue

        if tool_name not in available_tools:
            errors.append(
                f'Unknown tool "{tool_name}".'
            )
            continue

        if "args" not in tool_call:
            errors.append(
                f'Tool call {index} is missing the "args" key.'
            )
            continue

        args = tool_call["args"]

        if not isinstance(args, dict):
            errors.append(
                f'Arguments for "{tool_name}" must be a dictionary.'
            )
            continue

        tool_definition = available_tools[tool_name]

        expected_args = tool_definition.get(
            "arguments",
            {}
        )

        expected_arg_names = set(expected_args.keys())
        provided_arg_names = set(args.keys())

        # Required arguments that were not supplied
        missing_args = (
            expected_arg_names - provided_arg_names
        )

        for argument in missing_args:
            errors.append(
                f'Tool "{tool_name}" is missing required argument "{argument}".'
            )

        # Arguments supplied that the tool does not support
        unexpected_args = (
            provided_arg_names - expected_arg_names
        )

        for argument in unexpected_args:
            errors.append(
                f'Tool "{tool_name}" received unexpected argument "{argument}".'
            )


    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
    