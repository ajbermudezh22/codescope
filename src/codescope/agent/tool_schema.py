"""LiteLLM-compatible JSON schemas for the 4 Tools methods."""

TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "find_symbol",
            "description": (
                "Semantic search over documented symbols in the indexed repository. "
                "Use this first to locate entry points by intent."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query."},
                    "kind": {
                        "type": "string",
                        "description": "Optional filter: Function, Class, Method, Module.",
                        "enum": ["Function", "Class", "Method", "Module", "Variable"],
                    },
                    "k": {"type": "integer", "description": "Max hits (default 5)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "callers_of",
            "description": "Symbols that call the given symbol (reverse CALLS walk).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol_id": {"type": "string"},
                    "depth": {"type": "integer", "description": "1 (default) to 3."},
                },
                "required": ["symbol_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "callees_of",
            "description": "Symbols that the given symbol calls (forward CALLS walk).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol_id": {"type": "string"},
                    "depth": {"type": "integer", "description": "1 (default) to 3."},
                },
                "required": ["symbol_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_source",
            "description": "Return the full source code for a symbol's range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol_id": {"type": "string"},
                    "with_context_lines": {"type": "integer"},
                },
                "required": ["symbol_id"],
            },
        },
    },
]
