import os
import json
import numpy as np
import pandas as pd
from sqlalchemy import text
from pipeline.ingestion.wetland.fetch import fetch_wetlands
from shared.database import engine, Base
from shared.models.wetland import WetlandDetail

# ── CONFIGURATION ────────────────────────────────────────────────────────────

# List of states to process
STATES_CONFIG = [
    {
        "iso": "TN",
        "name": "Tennessee",
        "path": os.path.join(os.getcwd(), "data", "wetland", "TN_geodatabase_wetlands.gdb"),
        "layer": "TN_wetlands"
    },
    {
        "iso": "GA",
        "name": "Georgia",
        "path": os.path.join(os.getcwd(), "data", "wetland", "GA_geodatabase_wetlands.gdb"),
        "layer": "GA_Wetlands" 
    }
]

SOURCE = "NWI"

# Columns to map from raw data → model
COLUMN_MAP = {
    'NWI_ID':       'external_id',
    'ATTRIBUTE':    'classification_code',
    'WETLAND_TYPE': 'wetland_type',
    'ACRES':        'size_acres',
}

CORE_COLS = [
    'external_id', 'wetland_type', 'classification_code',
    'size_acres', 'state', 'source',
]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def to_scalar(val):
    if val is None:
        return None
    if isinstance(val, pd.Series):
        val = val.iloc[0] if len(val) > 0 else None
    try:
        if isinstance(val, float) and np.isnan(val):
            return None
    except TypeError:
        pass
    if isinstance(val, np.integer):  return int(val)
    if isinstance(val, np.floating): return float(val)
    if isinstance(val, np.bool_):    return bool(val)
    return val

def to_str(val):
    v = to_scalar(val)
    return str(v) if v is not None else None

def to_float(val):
    v = to_scalar(val)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

# ── CORE PROCESSOR ────────────────────────────────────────────────────────────

def process_state(state_cfg):
    state_iso = state_cfg['iso']
    gpkg_path = state_cfg['path']
    layer = state_cfg['layer']

    print(f"\n--- PROCESSING {state_cfg['name']} ({state_iso}) ---")

    if not os.path.exists(gpkg_path):
        print(f"  ❌ File not found: {gpkg_path}")
        return

    # 1. Load
    gdf = fetch_wetlands(gpkg_path, layer=layer)

    # 2. Reproject NAD83 Albers → EPSG:4326
    print(f"  Reprojecting from {gdf.crs} → EPSG:4326...")
    gdf = gdf.to_crs("EPSG:4326")

    # 3. Rename columns
    gdf = gdf.rename(columns=COLUMN_MAP).copy()

    # 4. Ensure core cols exist
    for col in CORE_COLS:
        if col not in gdf.columns:
            gdf[col] = None

    # 5. Attach state info
    gdf['state']  = state_iso
    gdf['source'] = SOURCE

    # 6. Validate geometries
    bad = gdf[gdf.geometry.is_empty | gdf.geometry.isna()]
    if len(bad):
        print(f"  ⚠️  Dropping {len(bad)} rows with null/empty geometry")
        gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]

    # 7. Force all geometries to MULTIPOLYGON
    from shapely.geometry import MultiPolygon, Polygon
    def ensure_multipolygon(geom):
        if geom is None:
            return None
        if isinstance(geom, Polygon):
            return MultiPolygon([geom])
        return geom

    gdf['geometry'] = gdf['geometry'].apply(ensure_multipolygon)
    print(f"  → {len(gdf)} valid records")

    # 8. Build insert rows
    print("  Building rows...")
    rows = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        rows.append({
            'external_id':         to_str(row.get('external_id')),
            'wetland_type':        to_str(row.get('wetland_type')),
            'classification_code': to_str(row.get('classification_code')),
            'size_acres':          to_float(row.get('size_acres')),
            'state':               state_iso,
            'source':              SOURCE,
            'geom':                f"SRID=4326;{geom.wkt}",
        })

    # 9. Delete existing records ONLY for this state/source
    with engine.begin() as conn:
        deleted = conn.execute(
            text("DELETE FROM wetland_details WHERE state = :state AND source = :source"),
            {'state': state_iso, 'source': SOURCE}
        )
        print(f"  🗑️ Removed {deleted.rowcount} existing {state_iso} records")

    # 10. Bulk insert
    INSERT_SQL = text("""
        INSERT INTO wetland_details (
            external_id, wetland_type, classification_code,
            size_acres, state, source, geom
        ) VALUES (
            :external_id, :wetland_type, :classification_code,
            :size_acres, :state, :source,
            ST_GeomFromEWKT(:geom)
        )
        ON CONFLICT (external_id) DO UPDATE SET
            wetland_type        = EXCLUDED.wetland_type,
            classification_code = EXCLUDED.classification_code,
            size_acres          = EXCLUDED.size_acres,
            state               = EXCLUDED.state,
            source              = EXCLUDED.source,
            geom                = EXCLUDED.geom,
            updated_at          = now()
    """)

    BATCH_SIZE = 500 
    total = len(rows)
    print(f"  📤 Inserting {total} records in batches of {BATCH_SIZE}...")

    try:
        with engine.begin() as conn:
            for i in range(0, total, BATCH_SIZE):
                batch = rows[i:i + BATCH_SIZE]
                conn.execute(INSERT_SQL, batch)
                if i % 5000 == 0:
                    print(f"    ✔ {min(i + BATCH_SIZE, total)}/{total}")
        print(f"  ✅ Done with {state_iso}")
    except Exception as e:
        print(f"  ❌ Insert failed for {state_iso}: {e}")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("Initializing schema...")
    Base.metadata.create_all(bind=engine)

    for state_cfg in STATES_CONFIG:
        process_state(state_cfg)

    print("\n🎉 All state ingestions completed.")

if __name__ == "__main__":
    main()