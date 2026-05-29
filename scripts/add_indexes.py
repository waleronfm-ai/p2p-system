import sqlite3
import time

DB_PATH = "data/p2p.db"

INDEXES = [
    (
        "ix_snap_combo",
        "CREATE INDEX IF NOT EXISTS ix_snap_combo ON snapshots (exchange, asset, fiat, trade_type, collected_at)",
    ),
    (
        "ix_snap_collected_at",
        "CREATE INDEX IF NOT EXISTS ix_snap_collected_at ON snapshots (collected_at)",
    ),
    (
        "ix_order_snapshot_id",
        "CREATE INDEX IF NOT EXISTS ix_order_snapshot_id ON orders (snapshot_id)",
    ),
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print(f"DB: {DB_PATH}\n")

for name, sql in INDEXES:
    t0 = time.perf_counter()
    cur.execute(sql)
    conn.commit()
    elapsed = time.perf_counter() - t0
    print(f"  {name}: {elapsed:.3f}s")

print("\nFinal index list from sqlite_master:")
cur.execute(
    "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY tbl_name, name"
)
for row in cur.fetchall():
    print(f"  [{row[1]}] {row[0]}")
    print(f"    {row[2]}")

conn.close()
