from app.db import connect


def _migrate(conn) -> None:
    """Add soft-delete columns / runs counters to databases created before
    the tombstone_retire module was implemented. Fresh databases get the full
    schema directly below, so this only runs against an old app.db."""
    canon_cols = {r["name"] for r in conn.execute("PRAGMA table_info(canonical_items)").fetchall()}
    for ddl in (
        "ALTER TABLE canonical_items ADD COLUMN status TEXT NOT NULL DEFAULT 'alive'",
        "ALTER TABLE canonical_items ADD COLUMN retired_at TEXT",
        "ALTER TABLE canonical_items ADD COLUMN retired_by_run_id INTEGER",
        "ALTER TABLE canonical_items ADD COLUMN retired_by_source_id INTEGER",
    ):
        col = ddl.split("ADD COLUMN")[1].split()[0]
        if col not in canon_cols:
            conn.execute(ddl)

    run_cols = {r["name"] for r in conn.execute("PRAGMA table_info(runs)").fetchall()}
    for ddl in (
        "ALTER TABLE runs ADD COLUMN retired_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE runs ADD COLUMN revived_count INTEGER NOT NULL DEFAULT 0",
    ):
        col = ddl.split("ADD COLUMN")[1].split()[0]
        if col not in run_cols:
            conn.execute(ddl)

    source_cols = {r["name"] for r in conn.execute("PRAGMA table_info(sources)").fetchall()}
    if "tombstone_source" not in source_cols:
        conn.execute(
            "ALTER TABLE sources ADD COLUMN tombstone_source INTEGER NOT NULL DEFAULT 0"
        )


def init_db():
    conn = connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS sources(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            format TEXT NOT NULL,
            fixture_path TEXT NOT NULL,
            watermark_ts TEXT,
            lookback_seconds INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            note TEXT,
            tombstone_source INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS runs(
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            parsed_count INTEGER NOT NULL,
            upserted_count INTEGER NOT NULL,
            conflict_count INTEGER NOT NULL,
            skipped_count INTEGER NOT NULL,
            retired_count INTEGER NOT NULL DEFAULT 0,
            revived_count INTEGER NOT NULL DEFAULT 0,
            report_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS staging_rows(
            id INTEGER PRIMARY KEY,
            run_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            business_key TEXT NOT NULL,
            event_ts TEXT NOT NULL,
            source_revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            disposition TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS canonical_items(
            id INTEGER PRIMARY KEY,
            business_key TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            event_ts TEXT NOT NULL,
            source_revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'alive',
            retired_at TEXT,
            retired_by_run_id INTEGER,
            retired_by_source_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS conflicts(
            id INTEGER PRIMARY KEY,
            run_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            business_key TEXT NOT NULL,
            existing_payload TEXT NOT NULL,
            incoming_payload TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    _migrate(conn)
    if conn.execute("SELECT COUNT(*) c FROM sources").fetchone()["c"] == 0:
        conn.executemany(
            """
            INSERT INTO sources(name, format, fixture_path, watermark_ts, lookback_seconds,
                                enabled, note, tombstone_source)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            [
                (
                    "Alpha Catalog",
                    "json",
                    "alpha_catalog.json",
                    None,
                    0,
                    1,
                    "clean：三件独立货号，首跑应全部 upsert",
                    0,
                ),
                (
                    "Beta Offers",
                    "jsonl",
                    "beta_offers.jsonl",
                    None,
                    0,
                    1,
                    "dirty：SKU-1001 与 Alpha 同键异价→冲突；另含独立货号",
                    0,
                ),
                (
                    "Gamma Shelf",
                    "xml",
                    "gamma_shelf.xml",
                    None,
                    0,
                    1,
                    "xml 源：两件独立货号",
                    0,
                ),
                (
                    "Delta Retirements",
                    "jsonl",
                    "delta_retirements.jsonl",
                    None,
                    0,
                    1,
                    "源级墓碑源：每行都是退役事件，对 SKU-1002 软删；含重复墓碑与未知键",
                    1,
                ),
                (
                    "Epsilon Revive Feed",
                    "jsonl",
                    "epsilon_revive.jsonl",
                    None,
                    0,
                    1,
                    "带内墓碑 + 复活：退役键上的新 revision 复活、旧 revision 拒绝",
                    0,
                ),
            ],
        )
        conn.execute("INSERT INTO settings(key, value) VALUES ('project_label', 'Feedstitch')")
        conn.execute("INSERT INTO settings(key, value) VALUES ('default_mode', 'incremental')")
        conn.commit()
    conn.close()
