import os
from datetime import datetime, timedelta
from sqlalchemy import text
from pipeline.ingestion.gas.price.fetch import fetch_gas_prices
from shared.database import engine, Base
from shared.models.gas_price import NaturalGasPrice, FrequencyEnum
import json

DAYS_BACK = 10
SOURCE    = "EIA"

def parse_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

def main():
    # 1. Schema
    print("Initializing schema...")
    Base.metadata.create_all(bind=engine)

    # 2. Fetch
    result      = fetch_gas_prices(days=DAYS_BACK)
    records     = result["records"]
    api_version = result["api_version"]

    if not records:
        print("❌ No records returned from API. Exiting.")
        return

    # 3. Build insert rows
    print("Building rows...")
    rows = []
    skipped = 0
    for rec in records:
        value = parse_float(rec.get("value"))
        if value is None:
            skipped += 1
            continue

        rows.append({
            "source":              SOURCE,
            "period":              rec.get("period"),           # "YYYY-MM-DD" string, pg casts it
            "duoarea":             rec.get("duoarea"),
            "area_name":           rec.get("areaName") or rec.get("area-name"),
            "product":             rec.get("product"),
            "product_name":        rec.get("productName") or rec.get("product-name"),
            "process":             rec.get("process"),
            "process_name":        rec.get("processName") or rec.get("process-name"),
            "series":              rec.get("series"),
            "series_description":  rec.get("seriesDescription") or rec.get("series-description"),
            "value":               value,
            "units":               rec.get("units"),
            "frequency":           FrequencyEnum.DAILY.value,
            "raw_metadata":        json.dumps(rec),
            "api_version":         api_version,
        })

    print(f"  → {len(rows)} valid rows | {skipped} skipped (null value)")

    # 4. Delete existing records for the same date window to prevent duplicates
    end_date   = datetime.today().date()
    start_date = end_date - timedelta(days=DAYS_BACK)

    with engine.begin() as conn:
        deleted = conn.execute(
            text("""
                DELETE FROM natural_gas_price
                WHERE source = :source
                  AND period >= :start_date
                  AND period <= :end_date
            """),
            {"source": SOURCE, "start_date": start_date, "end_date": end_date}
        )
        print(f"🗑️  Removed {deleted.rowcount} existing records in window")

    # 5. Bulk insert
    INSERT_SQL = text("""
        INSERT INTO natural_gas_price (
            source, period, duoarea, area_name,
            product, product_name, process, process_name,
            series, series_description, value, units,
            frequency, raw_metadata, api_version
        ) VALUES (
            :source, cast(:period as date), :duoarea, :area_name,
            :product, :product_name, :process, :process_name,
            :series, :series_description, :value, :units,
            cast(:frequency as frequencyenum), cast(:raw_metadata as jsonb), :api_version
        )
    """)

    BATCH_SIZE = 5
    total = len(rows)
    print(f"📤 Inserting {total} records in batches of {BATCH_SIZE}...")

    try:
        with engine.begin() as conn:
            for i in range(0, total, BATCH_SIZE):
                batch = rows[i:i + BATCH_SIZE]
                conn.execute(INSERT_SQL, batch)
                print(f"  ✔ {min(i + BATCH_SIZE, total)}/{total}")
        print(f"\n✅ Done. {total} natural gas price records loaded.")
    except Exception as e:
        print(f"\n❌ Insert failed: {e}")
        raise

if __name__ == "__main__":
    main()