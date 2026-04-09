import os
from google import genai
from google.genai import types

def get_llm_client():
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

async def generate_json(prompt: str, response_schema: type[dict] | type[list]) -> dict | list:
    try:
        client = get_llm_client()
        # NOTE: For google-genai async calls in older versions, 
        # run in threadpool if proper async is not available, 
        # but the modern google-genai SDK supports async: `client.aio.models.generate_content`
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.1
            ),
        )
        import json
        return json.loads(response.text)
    except Exception as e:
        print(f"LLM Error: {e}")
        return None
