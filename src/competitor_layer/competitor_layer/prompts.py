"""Prompt templates for Gemini-powered reasoning."""

SYNONYM_EXPANSION_PROMPT = """\
You are an expert in CPG (consumer packaged goods) ingredient sourcing.

Given the ingredient "{canonical_name}" (also known as: {aliases}), in the category "{category}":

1. List additional names, synonyms, trade names, E-numbers, or chemical variants that a supplier might use for this ingredient.
2. Suggest 5 specific search queries that a procurement specialist would use to find B2B suppliers for this ingredient. Focus on queries that would surface manufacturer websites, technical data sheets, and product catalogs.

Only include names and queries that are genuinely relevant to this specific ingredient in a {category} context. Be concise.
"""

SUPPLIER_REASONING_PROMPT = """\
You are an expert in CPG ingredient sourcing and supplier evaluation.

Given this supplier candidate found via web search:
- Supplier: {supplier_name}
- Type: {supplier_type}
- Country: {country}
- Website: {website}
- Search results found: {result_count}
- Evidence: product page {product_page}, PDF {pdf}, technical docs {tech_doc}
- Ingredient searched: {ingredient_name}

Write a concise 1-2 sentence explanation of why this supplier is or isn't a good candidate for sourcing {ingredient_name}. Focus on concrete evidence signals. Do not speculate beyond what the evidence shows.
"""

SUPPLIER_CLASSIFICATION_PROMPT = """\
You are an expert in CPG supply chain classification.

Based on the following search result titles and snippets from a company's website, classify this company's primary business role for ingredient supply.

Company domain: {domain}
Search results:
{results_text}

Classify as one of: manufacturer, distributor, reseller, unknown.
Only classify as manufacturer if there is evidence they produce/manufacture the ingredient themselves.
Only classify as distributor if they primarily distribute/wholesale ingredients from other manufacturers.
Classify as reseller if they primarily sell to end consumers (B2C).
If unclear, classify as unknown.
"""
