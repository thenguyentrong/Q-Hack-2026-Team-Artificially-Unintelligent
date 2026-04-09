import json
import os

from google import genai
from google.genai import types

from src.preprocessing_layer.model_config import DEFAULT_MODEL


def get_llm_client():
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


async def generate_json(prompt: str, response_schema: type[dict] | type[list]) -> dict | list:
    try:
        client = get_llm_client()
        response = await client.aio.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.1
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"LLM Error: {e}")
        return None
