from fastapi import FastAPI
from .models import PreprocessingInput, MyIngredientOutput, IngredientOutput, ContextOutput

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

    return MyIngredientOutput(
        schema_version="1.0",
        ingredient=IngredientOutput(
            ingredient_id=input_data.RM_sku,
            canonical_name=canonical_name,
            aliases=[]
        ),
        context=ContextOutput(
            product_category="Unknown",
            region="Global"
        ),
        baseline_supplier=None
    )
