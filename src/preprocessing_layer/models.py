from pydantic import BaseModel, Field
from typing import List, Optional

class PreprocessingInput(BaseModel):
    schema_version: str
    company_id: int
    company_name: str
    RM_id: str
    RM_sku: str

class IngredientOutput(BaseModel):
    ingredient_id: str
    canonical_name: str
    aliases: List[str]

class ContextOutput(BaseModel):
    product_category: str
    region: str

class MyIngredientOutput(BaseModel):
    schema_version: str
    ingredient: IngredientOutput
    context: ContextOutput
    baseline_supplier: Optional[str] = None
