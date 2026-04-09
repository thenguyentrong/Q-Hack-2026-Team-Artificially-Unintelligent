"""
catalog_db.py  – Synchronous SQLite helpers for the FastAPI catalog endpoints.
Reads directly from data/db.sqlite (the real dataset).
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

# Resolve DB path relative to the project root
_DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "db.sqlite"
DB_PATH = os.environ.get("DB_PATH", str(_DEFAULT_DB))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sku_to_name(sku: str) -> str:
    """Convert a raw-material SKU like 'RM-C28-whey-protein-isolate-8956b79c' → 'Whey Protein Isolate'."""
    # Strip prefix RM-Cnn- and trailing -hexhash
    name = re.sub(r"^RM-C\d+-", "", sku)
    name = re.sub(r"-[0-9a-f]{8}$", "", name)
    return name.replace("-", " ").title()


def get_finished_goods(limit: int = 10) -> list[dict[str, Any]]:
    """Return finished-good products with company name."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT P.Id, P.SKU, C.Name AS company
            FROM Product P
            JOIN Company C ON P.CompanyId = C.Id
            WHERE P.Type = 'finished-good'
            ORDER BY P.Id
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_bom_for_fg(fg_sku: str) -> list[dict[str, Any]]:
    """Return BOM components for a finished-good SKU."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                RM.SKU          AS rm_sku,
                RC.Name         AS rm_company,
                COUNT(SP.SupplierId) AS supplier_count
            FROM Product FG
            JOIN BOM B ON B.ProducedProductId = FG.Id
            JOIN BOM_Component BC ON BC.BOMId = B.Id
            JOIN Product RM ON RM.Id = BC.ConsumedProductId
            JOIN Company RC ON RC.Id = RM.CompanyId
            LEFT JOIN Supplier_Product SP ON SP.ProductId = RM.Id
            WHERE FG.SKU = ?
            GROUP BY RM.SKU, RC.Name
            ORDER BY supplier_count DESC
            """,
            (fg_sku,),
        )
        rows = cur.fetchall()
        components = []
        for r in rows:
            d = dict(r)
            d["name"] = _sku_to_name(d["rm_sku"])
            components.append(d)
        return components
    finally:
        conn.close()


def get_all_suppliers() -> list[dict[str, Any]]:
    """Return all suppliers."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT Id, Name FROM Supplier ORDER BY Name")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_suppliers_for_rm(rm_sku: str) -> list[str]:
    """Return supplier names for a raw-material SKU."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT S.Name
            FROM Supplier_Product SP
            JOIN Supplier S ON SP.SupplierId = S.Id
            JOIN Product P ON SP.ProductId = P.Id
            WHERE P.SKU = ?
            """,
            (rm_sku,),
        )
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def get_top_raw_materials(limit: int = 10) -> list[dict[str, Any]]:
    """Return the most-used raw materials across all BOMs."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                P.SKU,
                C.Name  AS company,
                COUNT(BC.BOMId) AS usage_count
            FROM BOM_Component BC
            JOIN Product P ON BC.ConsumedProductId = P.Id
            JOIN Company C ON P.CompanyId = C.Id
            GROUP BY P.SKU
            ORDER BY usage_count DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["name"] = _sku_to_name(d["SKU"])
            result.append(d)
        return result
    finally:
        conn.close()
