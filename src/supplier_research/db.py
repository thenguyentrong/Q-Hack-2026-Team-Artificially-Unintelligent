from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parents[2] / "data" / "db.sqlite"


def get_suppliers_for_ingredient(ingredient_name: str, db_path: Path = _DB_PATH) -> list[dict]:
    """Return distinct suppliers that carry a raw-material matching the ingredient name.

    Matching is done on the SKU slug (spaces → hyphens, lower-cased).
    Multiple SKUs from the same supplier are collapsed into one row.
    """
    slug = ingredient_name.lower().replace(" ", "-")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                s.Id   AS supplier_id,
                s.Name AS supplier_name,
                GROUP_CONCAT(DISTINCT p.SKU) AS skus
            FROM Supplier s
            JOIN Supplier_Product sp ON s.Id = sp.SupplierId
            JOIN Product p           ON sp.ProductId = p.Id
            WHERE p.Type = 'raw-material'
              AND p.SKU LIKE ?
            GROUP BY s.Id, s.Name
            ORDER BY s.Name
            """,
            (f"%{slug}%",),
        ).fetchall()

    return [
        {
            "supplier_id": r["supplier_id"],
            "supplier_name": r["supplier_name"],
            "skus": r["skus"].split(","),
        }
        for r in rows
    ]
