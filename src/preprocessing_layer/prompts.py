def get_aliases_prompt(canonical_name: str) -> str:
    return f"List 3-5 common chemical/trade aliases for the ingredient '{canonical_name}'. Return ONLY a JSON array of strings."

def get_category_prompt_no_fgs(canonical_name: str) -> str:
    return f"What is the most likely high-level product category (e.g., 'Personal Care / Cosmetics', 'Food & Beverage', 'Pharmaceuticals') for an ingredient named '{canonical_name}'? Return a JSON object with a single key 'category'."

def get_category_prompt_with_fgs(canonical_name: str, fgs: list) -> str:
    return f"An ingredient named '{canonical_name}' is used to manufacture the following finished goods SKUs: {fgs}. Based on these SKUs, what is the most likely high-level product category (e.g., 'Personal Care / Cosmetics', 'Food & Beverage', 'Pharmaceuticals')? Return a JSON object with a single key 'category'."
