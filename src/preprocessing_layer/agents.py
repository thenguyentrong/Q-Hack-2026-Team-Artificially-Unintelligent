from .db_client import get_finished_goods_for_rm, get_supplier_for_rm
from .llm_client import generate_json
from .prompts import (
    get_aliases_prompt,
    get_category_prompt_no_fgs,
    get_category_prompt_with_fgs,
)


async def run_aliases_agent(canonical_name: str) -> list[str]:
    prompt = get_aliases_prompt(canonical_name)
    # Define schema for Gemini: A list of strings
    schema = {"type": "ARRAY", "items": {"type": "STRING"}}
    result = await generate_json(prompt, schema)
    if isinstance(result, list):
        return result
    return []


async def run_context_agent(rm_sku: str, canonical_name: str) -> str:
    fgs = await get_finished_goods_for_rm(rm_sku)

    if not fgs:
        prompt = get_category_prompt_no_fgs(canonical_name)
    else:
        prompt = get_category_prompt_with_fgs(canonical_name, fgs)

    schema = {"type": "OBJECT", "properties": {"category": {"type": "STRING"}}}
    result = await generate_json(prompt, schema)
    if isinstance(result, dict) and "category" in result:
        return result["category"]
    return "Unknown"


async def run_supplier_agent(rm_sku: str) -> str | None:
    # Pure DB task
    return await get_supplier_for_rm(rm_sku)
