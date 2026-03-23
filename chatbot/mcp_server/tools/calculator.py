import numexpr as ne

def calculator(data):

    expression = data["expression"]

    print("[MCP] calculator ->", expression)

    try:
        result = ne.evaluate(expression)
        return {"result": str(result)}

    except Exception as e:
        return {"result": f"Calculation error: {str(e)}"}