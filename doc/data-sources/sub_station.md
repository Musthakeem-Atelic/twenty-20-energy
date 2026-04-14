# Technical Documentation: Electricity Substation Ingestion Pipeline

This document outlines the ETL (Extract, Transform, Load) workflow used to ingest electricity substation footprints into our spatial database for Georgia and Tennessee. These records help the platform understand where interconnection infrastructure already exists near candidate land parcels.

## 1. Data Source & Coverage
The pipeline loads state-level **OpenStreetMap (OSM)** substation exports from local GeoJSON files. Each run processes one file for **Georgia** and one for **Tennessee**, then merges them into a single normalized dataset.

* **Input Files:** `data/electricity/sub_station/georgia_substations.geojson` and `data/electricity/sub_station/tennessee_substations.geojson`
* **Data Type:** Polygon / MultiPolygon vector features
* **Source Identifier:** `OSM`

---

## 2. Ingestion Workflow Summary
The substation pipeline follows a geometry-first process so that only valid, state-scoped infrastructure reaches PostGIS.

### **Phase 1: GeoJSON Loading**
The fetch step reads each state GeoJSON file with `geopandas`. The loader keeps the original geometry and all source attributes so the later stages can both normalize the core schema and preserve unmapped metadata.

### **Phase 2: CRS Alignment & Spatial Validation**
Before filtering, the pipeline verifies the coordinate reference system:
* If the source file has no CRS, it is assigned **EPSG:4326 (WGS 84)**.
* If the source file uses another CRS, it is reprojected to **EPSG:4326**.

The pipeline then performs a **spatial join** against the U.S. state shapefile (`data/us_states/tl_2023_us_state.shp`) and keeps only features intersecting **GA** and **TN**.

### **Phase 3: Attribute Cleaning & Geometry Normalization**
The cleaner standardizes the OSM attributes into our internal schema:
* **Voltage Parsing:** Raw values such as `161000` or `161000;115000` are converted into a single numeric voltage field.
* **Geometry Normalization:** Single `Polygon` features are wrapped into `MultiPolygon` geometry so the database receives a consistent spatial type.
* **Invalid Geometry Removal:** Empty or unsupported shapes are dropped before insertion.

### **Phase 4: Final Row Construction**
After cleaning, the task layer:
1. Maps OSM tags such as `@id`, `operator:short`, `operator:wikidata`, and `substation`.
2. Forces the state context from the per-file config to guarantee consistent `state_iso` and `state_name` values.
3. Preserves all remaining source attributes inside `raw_metadata` as JSONB for forward compatibility.

---

## 3. Data Schema & Content
The `electricity_substation` table stores both the business-friendly substation fields and the original source context.

| Category | Attributes Captured | Details & Units |
| :--- | :--- | :--- |
| **Identification** | `source`, `osm_id`, `name`, `ref` | Core identifiers and human-readable labels from OSM. |
| **Operator** | `operator`, `operator_short`, `operator_wikidata`, `operator_wikipedia` | Utility or authority operating the substation. |
| **Electrical** | `voltage` | Stored as a numeric voltage value in **Volts**. |
| **Electrical** | `substation_type` | OSM classification such as transmission, distribution, or generation. |
| **Site Context** | `location` | Installation context such as outdoor, indoor, or underground. |
| **Administrative** | `state_iso`, `state_name`, `country` | Geographic attribution used for filtering and display. |
| **Metadata** | `raw_metadata` | All non-core source properties retained in JSONB format. |
| **Geometry** | `geom` | PostGIS MultiPolygon geometry in **SRID 4326**. |

---

## 4. Database Storage & Sync Strategy
The pipeline uses a full refresh pattern for OSM substations:

1. **Schema Initialization:** The SQLAlchemy metadata ensures the `electricity_substation` table exists before ingestion begins.
2. **Source-Specific Cleanup:** Existing records where `source = 'OSM'` are deleted before new rows are inserted.
3. **PostGIS Serialization:** Cleaned geometries are converted to **EWKT** and inserted with `ST_GeomFromEWKT`, then wrapped with `ST_Multi` to guarantee multipolygon storage.
4. **Batch Inserts:** Records are inserted in **batches of 100** to keep transactions efficient and stable.

---

## 5. Value for Land Selection
This substation layer supports several high-value siting and infrastructure workflows:
* **Grid Proximity Screening:** Identify parcels near existing substations that may reduce interconnection distance.
* **Utility Context:** Surface the operator and substation type to help users understand who controls nearby infrastructure.
* **Capacity Signals:** Use voltage data as an initial proxy when evaluating whether nearby infrastructure may support larger energy projects.
* **Map Intelligence:** Render polygon footprints instead of only point markers, giving users a more realistic view of infrastructure occupation on the landscape.
