from fastapi import FastAPI
import asyncio
from .models import PreprocessingInput, MyIngredientOutput, IngredientOutput, ContextOutput
from .agents import run_aliases_agent, run_context_agent, run_supplier_agent

app = FastAPI(title="Preprocessing Layer API")

@app.post("/api/v1/preprocess", response_model=MyIngredientOutput)
async def preprocess_ingredient(input_data: PreprocessingInput):
    # Synchronous Extraction
    parts = input_data.RM_sku.split('-')
    if len(parts) >= 4:
        # e.g., RM-C56-citric-acid-d55c874f -> "citric acid"
        canonical_name = " ".join(parts[2:-1])
    else:
        canonical_name = input_data.RM_sku

    # Run Parallel Agents
    aliases_task = run_aliases_agent(canonical_name)
    context_task = run_context_agent(input_data.RM_sku, canonical_name)
    supplier_task = run_supplier_agent(input_data.RM_sku)

    aliases, category, supplier = await asyncio.gather(
        aliases_task, context_task, supplier_task
    )

    return MyIngredientOutput(
        schema_version="1.0",
        ingredient=IngredientOutput(
            ingredient_id=input_data.RM_sku,
            canonical_name=canonical_name,
            aliases=aliases
        ),
        context=ContextOutput(
            product_category=category,
            region="Global"
        ),
        baseline_supplier=supplier
    )
