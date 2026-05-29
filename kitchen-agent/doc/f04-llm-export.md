Exporting the `GenerateContentConfig` (which contains your tool schemas) to JSON is one of the best debugging techniques you can use. It allows you to see _exactly_ what the Gemini API sees when it reads your tool descriptions.

Because the new `google-genai` SDK uses Pydantic under the hood for its types, serializing the configuration to JSON is incredibly easy.

Here are two ways you can do it:

### Method 1: Quick Print in `agent.py` (For immediate debugging)

You can temporarily add a print statement right before you call the Gemini API in your `agent.py` file.

```python
# Inside agent.py, right after you define `config`

config = types.GenerateContentConfig(
    tools=[_gemini_tools],
    temperature=settings.gemini_temperature,
    system_instruction=system_instruction,
)

# --- DEBUGGING: Print the config as JSON ---
# Because GenerateContentConfig is a Pydantic model in the new SDK,
# you can use model_dump_json()
print(config.model_dump_json(indent=2, exclude_none=True))
# -----------------------------------------

response = _client.models.generate_content(...)
```

### Method 2: Create a dedicated export script (Recommended)

If you want to save it to a file so you can inspect it in your code editor, you can create a quick script in your project root (e.g., `export_schema.py`):

```python
# export_schema.py
import json
from google.genai import types
from src.tools.registry import DECLARATIONS
from src.config import settings

def export_config_to_json():
    # 1. Build the tool and config exactly as the agent does
    gemini_tools = types.Tool(function_declarations=DECLARATIONS)

    config = types.GenerateContentConfig(
        tools=[gemini_tools],
        temperature=settings.gemini_temperature,
        system_instruction="You are a helpful assistant."
    )

    # 2. Dump to JSON string
    # exclude_none=True keeps the JSON clean by removing empty optional fields
    config_json = config.model_dump_json(indent=2, exclude_none=True)

    # 3. Write to a file
    with open("debug_gemini_config.json", "w", encoding="utf-8") as f:
        f.write(config_json)

    print("✅ Successfully exported config to debug_gemini_config.json")

if __name__ == "__main__":
    export_config_to_json()
```

### Why this is so useful for debugging:

When you open that `debug_gemini_config.json` file, you will see the raw OpenAPI-style schema that Google's servers process.

You can use this to verify:

1. **Descriptions:** Are your descriptions detailed enough? (e.g., checking if the `edit_file` description actually contains the warning about using `read_file` first).
2. **Required Fields:** Did you accidentally make a parameter optional when it should be required?
3. **Type Mismatches:** Did you specify a parameter as an `OBJECT` when it should be a `STRING`?

If the LLM is acting "dumb" or ignoring a tool, looking at this JSON file is always the first step to figuring out why!
