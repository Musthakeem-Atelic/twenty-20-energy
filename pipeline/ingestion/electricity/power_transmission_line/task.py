import os
import json
import numpy as np
import pandas as pd
from sqlalchemy import text
from pipeline.ingestion.electricity.power_transmission_line.fetch import fetch_electricity_lines
from pipeline.ingestion.gas.gas_pipeline.clean import filter_states          # reuse existing filter
from shared.database import engine, Base
from shared.models.electricity_transmission_line import ElectricityTransmissionLine

BASE_DIR       = os.getcwd()
GEOJSON_PATH   = os.path.join(BASE_DIR, "data", "electricity", "power_transmission_lines", "US_Electric_Power_Transmission_Lines_-6976209181916424225.geojson")
STATES_SHAPEFILE = os.path.join(BASE_DIR, "data", "us_states", "tl_2023_us_state.shp")

# GeoJSON property keys → model column names
PROPERTY_MAP = {
    'ID':         'line_id',
    'TYPE':       'line_type',
    'STATUS':     'status',
    'OWNER':      'owner',
    'VOLTAGE':    'voltage',
    'VOLT_CLASS': 'volt_class',
    'SUB_1':      'sub_1',
    'SUB_2':      'sub_2',
    'INFERRED':   'inferred',
    'STUSPS':     'state_iso',   # comes from spatial join — rename AFTER filter
    'NAME':       'state_name',
}

CORE_COLS = [
    'source', 'line_id', 'owner', 'status', 'line_type',
    'voltage', 'volt_class', 'sub_1', 'sub_2', 'inferred',
    'state_iso', 'state_name',
]

# ── helpers ───────────────────────────────────────────────────────────────────

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
        f = float(v)
        return None if f == -999999 else f
    except (TypeError, ValueError):
        return None

def build_metadata(row, exclude):
    record = {}
    for col in row.index:
        if col in exclude:
            continue
        try:
            v = to_scalar(row[col])
            json.dumps(v)
            record[col] = v
        except (TypeError, ValueError):
            record[col] = str(row[col])
    return json.dumps(record)

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # 1. Schema
    print("Initializing schema...")
    Base.metadata.create_all(bind=engine)

    # 2. Load GeoJSON
    gdf = fetch_electricity_lines(GEOJSON_PATH)

    # 3. Reproject to EPSG:4326 if needed
    if gdf.crs.to_epsg() != 4326:
        print("Reprojecting to EPSG:4326...")
        gdf = gdf.to_crs("EPSG:4326")

    # 4. Spatial filter — STUSPS and NAME are attached here by the join
    print("Filtering to TN/GA...")
    gdf = filter_states(gdf, STATES_SHAPEFILE)
    print(f"  → {len(gdf)} records after spatial filter")

    # 5. Rename ALL columns (including STUSPS/NAME from join) AFTER filter
    gdf = gdf.rename(columns=PROPERTY_MAP).copy()

    # 6. Ensure all core cols exist
    for col in CORE_COLS:
        if col not in gdf.columns:
            gdf[col] = None
    gdf['source'] = 'HIFLD'

    # 7. Validate geometries
    bad = gdf[gdf.geometry.is_empty | gdf.geometry.isna()]
    if len(bad):
        print(f"  ⚠️  Dropping {len(bad)} rows with null/empty geometry")
        gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    print(f"  → {len(gdf)} valid geometries")

    # 8. Print geometry types so we know what we're dealing with
    geom_types = gdf.geometry.geom_type.value_counts()
    print(f"  Geometry types:\n{geom_types.to_string()}")

    # 9. Build insert rows — normalize all geometry to WKT
    print("Building rows...")
    exclude_from_meta = set(CORE_COLS) | {'geometry'}
    rows = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        rows.append({
            'source':       'HIFLD',
            'line_id':      to_str(row.get('line_id')),
            'owner':        to_str(row.get('owner')),
            'status':       to_str(row.get('status')),
            'line_type':    to_str(row.get('line_type')),
            'voltage':      to_float(row.get('voltage')),
            'volt_class':   to_str(row.get('volt_class')),
            'sub_1':        to_str(row.get('sub_1')),
            'sub_2':        to_str(row.get('sub_2')),
            'inferred':     to_str(row.get('inferred')),
            'state_iso':    to_str(row.get('state_iso')),
            'state_name':   to_str(row.get('state_name')),
            'raw_metadata': build_metadata(row, exclude_from_meta),
            'geom':         f"SRID=4326;{geom.wkt}",
        })

    # 10. Delete existing HIFLD records
    with engine.begin() as conn:
        deleted = conn.execute(
            text("DELETE FROM electricity_transmission_line WHERE source = 'HIFLD'")
        )
        print(f"🗑️  Removed {deleted.rowcount} existing HIFLD records")

    # 11. Bulk insert
    INSERT_SQL = text("""
        INSERT INTO electricity_transmission_line (
            source, line_id, owner, status, line_type,
            voltage, volt_class, sub_1, sub_2, inferred,
            state_iso, state_name, raw_metadata, geom
        ) VALUES (
            :source, :line_id, :owner, :status, :line_type,
            :voltage, :volt_class, :sub_1, :sub_2, :inferred,
            :state_iso, :state_name,
            cast(:raw_metadata as jsonb),
            ST_GeomFromEWKT(:geom)
        )
    """)

    BATCH_SIZE = 100
    total = len(rows)
    print(f"📤 Inserting {total} records in batches of {BATCH_SIZE}...")

    try:
        with engine.begin() as conn:
            for i in range(0, total, BATCH_SIZE):
                batch = rows[i:i + BATCH_SIZE]
                conn.execute(INSERT_SQL, batch)
                print(f"  ✔ {min(i + BATCH_SIZE, total)}/{total}")
        print(f"\n✅ Done. {total} records loaded into electricity_transmission_line.")
    except Exception as e:
        print(f"\n❌ Insert failed: {e}")
        raise

if __name__ == "__main__":
    main()