import sqlite3, re

conn = sqlite3.connect("data/db.sqlite")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get top finished goods with most BOM components
print("=== TOP FINISHED GOODS BY BOM SIZE ===")
cur.execute("""
    SELECT FG.SKU, C.Name as company, COUNT(BC.ConsumedProductId) as component_count
    FROM BOM B
    JOIN Product FG ON B.ProducedProductId = FG.Id
    JOIN Company C ON FG.CompanyId = C.Id
    JOIN BOM_Component BC ON B.Id = BC.BOMId
    GROUP BY FG.SKU
    ORDER BY component_count DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(dict(r))

print("\n=== ALL UNIQUE SUPPLIERS ===")
cur.execute("SELECT Id, Name FROM Supplier ORDER BY Name")
for r in cur.fetchall():
    print(dict(r))

print("\n=== TOP RAW MATERIALS (most used in BOMs) ===")
cur.execute("""
    SELECT P.SKU, C.Name as company, COUNT(BC.BOMId) as usage_count
    FROM BOM_Component BC
    JOIN Product P ON BC.ConsumedProductId = P.Id
    JOIN Company C ON P.CompanyId = C.Id
    GROUP BY P.SKU
    ORDER BY usage_count DESC
    LIMIT 15
""")
for r in cur.fetchall():
    print(dict(r))

conn.close()
