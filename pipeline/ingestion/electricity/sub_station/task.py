import os
import json
import numpy as np
import pandas as pd
from sqlalchemy import text

from pipeline.ingestion.electricity.sub_station.fetch import fetch_substations
from pipeline.ingestion.electricity.sub_station.clean import clean_substations
from shared.database import engine, Base


# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR = os.getcwd()

STATES_SHAPEFILE = os.path.join(
    BASE_DIR, "data", "us_states", "tl_2023_us_state.shp"
)

INPUT_FILES = [
    {
        "file": os.path.join(
            BASE_DIR,
            "data",
            "electricity",
            "sub_station",
            "georgia_substations.geojson",
        ),
        "state": "GA",
        "name": "Georgia",
    },
    {
        "file": os.path.join(
            BASE_DIR,
            "data",
            "electricity",
            "sub_station",
            "tennessee_substations.geojson",
        ),
        "state": "TN",
        "name": "Tennessee",
    },
]


# ── Mapping ───────────────────────────────────────────────────────────────────

PROPERTY_MAP = {
    "@id": "osm_id",
    "name": "name",
    "ref": "ref",
    "operator": "operator",
    "operator:short": "operator_short",
    "operator:wikidata": "operator_wikidata",
    "operator:wikipedia": "operator_wikipedia",
    "voltage": "voltage_raw",
    "substation": "substation_type",
    "location": "location",
    "country": "country",
    "STUSPS": "state_iso",
    "NAME": "state_name",
}

CORE_COLS = [
    "source",
    "osm_id",
    "name",
    "ref",
    "operator",
    "operator_short",
    "operator_wikidata",
    "operator_wikipedia",
    "voltage",
    "substation_type",
    "location",
    "state_iso",
    "state_name",
    "country",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

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

    if isinstance(val, np.integer):
        return int(val)

    if isinstance(val, np.floating):
        return float(val)

    if isinstance(val, np.bool_):
        return bool(val)

    return val


def to_str(val):
    v = to_scalar(val)
    return str(v) if v is not None else None


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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Initializing schema...")
    Base.metadata.create_all(bind=engine)

    all_gdfs = []

    # ── Load + clean per state ────────────────────────────────────────────────
    for cfg in INPUT_FILES:
        file_path = cfg["file"]
        state_code = cfg["state"]
        state_name = cfg["name"]

        print(f"\n📂 Loading {state_name} ({state_code})")

        gdf = fetch_substations(file_path)

        gdf = gdf.rename(columns=PROPERTY_MAP).copy()

        gdf = clean_substations(gdf, STATES_SHAPEFILE)

        if gdf is None or len(gdf) == 0:
            continue

        # 🔥 FORCE STATE INFO (important improvement)
        gdf["state_iso"] = state_code
        gdf["state_name"] = state_name

        gdf["source"] = "OSM"

        all_gdfs.append(gdf)

    if not all_gdfs:
        print("❌ No valid data found.")
        return

    gdf = pd.concat(all_gdfs, ignore_index=True)

    print(f"\n✅ Total merged records: {len(gdf)}")

    # ── Ensure columns ────────────────────────────────────────────────────────
    for col in CORE_COLS:
        if col not in gdf.columns:
            gdf[col] = None

    # ── Build rows ────────────────────────────────────────────────────────────
    print("Building rows...")

    exclude_from_meta = set(CORE_COLS) | {"geometry", "geom_clean", "voltage_raw"}

    rows = []

    for _, row in gdf.iterrows():
        geom = row.geometry

        rows.append(
            {
                "source": "OSM",
                "osm_id": to_str(row.get("osm_id")),
                "name": to_str(row.get("name")),
                "ref": to_str(row.get("ref")),
                "operator": to_str(row.get("operator")),
                "operator_short": to_str(row.get("operator_short")),
                "operator_wikidata": to_str(row.get("operator_wikidata")),
                "operator_wikipedia": to_str(row.get("operator_wikipedia")),
                "voltage": to_scalar(row.get("voltage")),
                "substation_type": to_str(row.get("substation_type")),
                "location": to_str(row.get("location")),
                "state_iso": to_str(row.get("state_iso")),
                "state_name": to_str(row.get("state_name")),
                "country": to_str(row.get("country")),
                "raw_metadata": build_metadata(row, exclude_from_meta),
                "geom": f"SRID=4326;{geom.wkt}",
            }
        )

    # ── Delete old records ────────────────────────────────────────────────────
    print("Removing old OSM records...")

    with engine.begin() as conn:
        deleted = conn.execute(
            text("DELETE FROM electricity_substation WHERE source = 'OSM'")
        )

        print(f"🗑️ Removed {deleted.rowcount} existing records")

    # ── Insert ────────────────────────────────────────────────────────────────
    INSERT_SQL = text(
        """
        INSERT INTO electricity_substation (
            source, osm_id, name, ref,
            operator, operator_short, operator_wikidata, operator_wikipedia,
            voltage, substation_type, location,
            state_iso, state_name, country,
            raw_metadata, geom
        )
        VALUES (
            :source, :osm_id, :name, :ref,
            :operator, :operator_short, :operator_wikidata, :operator_wikipedia,
            :voltage, :substation_type, :location,
            :state_iso, :state_name, :country,
            CAST(:raw_metadata AS jsonb),
            ST_Multi(ST_GeomFromEWKT(:geom))
        )
        """
    )

    BATCH_SIZE = 100
    total = len(rows)

    print(f"\n📤 Inserting {total} records...")

    try:
        with engine.begin() as conn:
            for i in range(0, total, BATCH_SIZE):
                batch = rows[i : i + BATCH_SIZE]
                conn.execute(INSERT_SQL, batch)
                print(f"✔ {min(i + BATCH_SIZE, total)}/{total}")

        print("\n🎉 Done. All substations loaded successfully.")

    except Exception as e:
        print(f"\n❌ Insert failed: {e}")
        raise


if __name__ == "__main__":
    main()