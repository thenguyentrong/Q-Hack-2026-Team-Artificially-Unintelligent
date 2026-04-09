# src/preprocessing_layer/db_client.py
import aiosqlite
import os

DB_PATH = os.environ.get("DB_PATH", "data/db.sqlite")

async def get_finished_goods_for_rm(rm_sku: str) -> list[str]:
    query = """
    SELECT FG.SKU 
    FROM Product RM
    JOIN BOM_Component BC ON RM.Id = BC.ConsumedProductId
    JOIN BOM B ON BC.BOMId = B.Id
    JOIN Product FG ON B.ProducedProductId = FG.Id
    WHERE RM.SKU = ? AND RM.Type = 'raw-material'
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(query, (rm_sku,)) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        print(f"DB Error fetching FGs: {e}")
        return []

async def get_supplier_for_rm(rm_sku: str) -> str | None:
    query = """
    SELECT S.Name 
    FROM Product RM
    JOIN Supplier_Product SP ON RM.Id = SP.ProductId
    JOIN Supplier S ON SP.SupplierId = S.Id
    WHERE RM.SKU = ?
    LIMIT 1
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(query, (rm_sku,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        print(f"DB Error fetching supplier: {e}")
        return None
