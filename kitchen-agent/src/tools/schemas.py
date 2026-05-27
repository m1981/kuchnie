# src/tools/schemas.py

"""
This file contains the JSON schemas that tell the Gemini LLM what tools it has available,
what they do, and what parameters they require.
"""

read_file_fn = {
    "name": "read_file",
    "description": "Reads the full contents of a local markdown file from the knowledge base.",
    "parameters": {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Path to the file, e.g., 'data/test.md'",
            }
        },
        "required": ["filepath"],
    },
}

get_repo_map_fn = {
    "name": "get_repo_map",
    "description": "Scans the knowledge base and returns a list of all markdown files and their headers. Use this to figure out which file you need to read.",
    "parameters": {
        "type": "object",
        "properties": {}, # No parameters needed, it just scans the default directory
    },
}

edit_file_fn = {
    "name": "edit_file",
    # ADDED STRICT GUARDRAILS TO THE DESCRIPTION:
    "description": "Edits an existing file using exact search and replace. ONLY use this tool if the user EXPLICITLY asks you to update, change, or edit a file. DO NOT proactively edit files to add information unless commanded.",
    "parameters": {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Path to the file, e.g., 'data/test.md'",
            },
            "search_text": {
                "type": "string",
                "description": "The exact text currently in the file that you want to replace.",
            },
            "replace_text": {
                "type": "string",
                "description": "The new text to insert in place of the search_text.",
            }
        },
        "required": ["filepath", "search_text", "replace_text"],
    },
}