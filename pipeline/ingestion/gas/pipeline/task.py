import os
import json
import pandas as pd
import numpy as np
from sqlalchemy import text
from pipeline.ingestion.gas.pipeline.fetch import fetch_eia_pipelines
from pipeline.ingestion.gas.pipeline.clean import filter_states
from shared.database import engine, Base
from shared.models.gas_pipeline import NaturalGasPipeline

BASE_DIR = os.getcwd()
STATES_SHAPEFILE = os.path.join(BASE_DIR, "data", "us_states", "tl_2023_us_state.shp")

CORE_COLS = ['source', 'operator', 'status', 'pipeline_type', 'state_iso', 'state_name']

def to_scalar(val):
    """Safely extract a plain Python scalar from any pandas/numpy type."""
    if val is None:
        return None
    if isinstance(val, pd.Series):
        val = val.iloc[0] if len(val) > 0 else None
    if isinstance(val, float) and np.isnan(val):
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    if isinstance(val, (np.bool_,)):
        return bool(val)
    return val

def to_str(val):
    v = to_scalar(val)
    return str(v) if v is not None else None

def build_metadata(row, exclude):
    """Pack all non-core columns into a JSON-serializable dict."""
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

def main():
    # 1. Recreate table from model (only creates if not exists)
    print("Initializing schema...")
    Base.metadata.create_all(bind=engine)

    # 2. Fetch
    print("Fetching EIA pipeline data...")
    eia_raw = fetch_eia_pipelines()
    if eia_raw is None:
        print("❌ Fetch returned nothing. Exiting.")
        return

    # 3. Filter to TN/GA
    print(f"Filtering to states...")
    df = filter_states(eia_raw, STATES_SHAPEFILE)
    print(f"  → {len(df)} records after spatial filter")

    # 4. Reproject to EPSG:4326
    if df.crs.to_epsg() != 4326:
        print("Reprojecting to EPSG:4326...")
        df = df.to_crs("EPSG:4326")

    # 5. Rename columns to match schema
    df = df.rename(columns={
        'typepipe': 'pipeline_type',
        'STUSPS':   'state_iso',
        'NAME':     'state_name',
    }).copy()

    # 6. Ensure core cols exist
    for col in CORE_COLS:
        if col not in df.columns:
            df[col] = None
    df['source'] = 'EIA'

    # 7. Validate geometries
    print("Validating geometries...")
    invalid = df[df.geometry.is_empty | df.geometry.isna()]
    if len(invalid):
        print(f"  ⚠️  Dropping {len(invalid)} rows with null/empty geometry")
        df = df[~df.geometry.is_empty & df.geometry.notna()]
    print(f"  → {len(df)} valid records")

    # 8. Build insert rows
    print("Building rows...")
    exclude_from_meta = set(CORE_COLS) | {'geometry'}
    rows = []
    for _, row in df.iterrows():
        geom = row.geometry
        rows.append({
            'source':        to_str(row.get('source')),
            'operator':      to_str(row.get('operator')),
            'status':        to_str(row.get('status')),
            'pipeline_type': to_str(row.get('pipeline_type')),
            'state_iso':     to_str(row.get('state_iso')),
            'state_name':    to_str(row.get('state_name')),
            'raw_metadata':  build_metadata(row, exclude_from_meta),
            'geom':          f"SRID=4326;{geom.wkt}",
        })

    # 9. Delete old EIA records
    with engine.begin() as conn:
        deleted = conn.execute(
            text("DELETE FROM natural_gas_pipeline WHERE source = 'EIA'")
        )
        print(f"🗑️  Removed {deleted.rowcount} existing EIA records")

    # 10. Bulk insert in batches
    INSERT_SQL = text("""
        INSERT INTO natural_gas_pipeline
            (source, operator, status, pipeline_type, state_iso, state_name, raw_metadata, geom)
        VALUES (
            :source,
            :operator,
            :status,
            :pipeline_type,
            :state_iso,
            :state_name,
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
        print(f"\n✅ Done. {total} records loaded into natural_gas_pipeline.")
    except Exception as e:
        print(f"\n❌ Insert failed: {e}")
        raise

if __name__ == "__main__":
    main()