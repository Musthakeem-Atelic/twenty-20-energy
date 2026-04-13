# Technical Documentation: Natural Gas Pipeline Ingestion Pipeline

This document details the automated ETL (Extract, Transform, Load) process for integrating the U.S. Natural Gas Pipeline network data into our spatial database, focusing specifically on Georgia and Tennessee infrastructure.

## 1. Data Source & Live Connectivity
The pipeline connects directly to the **U.S. Energy Information Administration (EIA)** via the Department of Transportation (DOT) ArcGIS Feature Server. This provides the most current national view of natural gas interstate and intrastate transmission pipelines.

* **Live Source:** [EIA Natural Gas Pipelines - ArcGIS Feature Server](https://geo.dot.gov/server/rest/services/Hosted/Natural_Gas_Pipelines_US_EIA/FeatureServer/0)
* **Data Type:** MultiLineString (Vector spatial data).
* **Source Identifier:** `EIA`

---

## 2. Ingestion Workflow Summary
The pipeline utilizes an API-first approach to fetch, filter, and normalize energy infrastructure data.

### **Phase 1: Geographic Bounding-Box Fetch**
Unlike bulk file downloads, the system requests data via an **ESRI Geometry Envelope**.
* **Bounding Box:** The fetcher uses specific coordinates (`-90.31, 30.35` to `-80.84, 36.67`) to limit the initial request to the Southeastern U.S. (TN and GA vicinity).
* **Geometry Extraction:** Raw JSON "paths" from the ArcGIS server are converted into **Shapely MultiLineString** objects for spatial processing.

### **Phase 2: Exact Spatial Filtering**
After the initial API fetch, a secondary, high-precision filter is applied:
1.  **State Geometry Join:** The system performs a **Spatial Join (`sjoin`)** against high-resolution U.S. Census state shapefiles.
2.  **Intersection Logic:** Only pipeline segments that physically intersect the boundaries of **Georgia** and **Tennessee** are retained.
3.  **Coordinate Standardization:** All data is forced into **EPSG:4326 (WGS 84)** to ensure it aligns perfectly with our land-parcel layers.

### **Phase 3: Schema Normalization & Preservation**
The pipeline maps proprietary EIA fields to our internal standard while ensuring 0% data loss:
* **Mapped Columns:** `typepipe` → `pipeline_type`, `operator` → `operator`, and `status`.
* **Full Preservation:** Every original attribute from the EIA server (such as ObjectIDs and shape lengths) is captured and stored in a **JSONB** column named `raw_metadata`.

---

## 3. Data Schema & Content
The `natural_gas_pipeline` table provides a detailed profile of the energy infrastructure passing through or near project sites.

| Category | Attributes Captured | Details |
| :--- | :--- | :--- |
| **Identification** | `source` | Labeled as `EIA` for tracking. |
| **Operational** | `operator` | The company responsible for the pipeline (e.g., Southern Natural Gas). |
| **Operational** | `status` | Current state of the line (e.g., Active). |
| **Technical** | `pipeline_type` | Classification of the pipeline (e.g., Transmission). |
| **Location** | `state_iso` / `state_name` | The ISO code (GA/TN) and full name assigned via spatial join. |
| **Metadata** | `raw_metadata` | Flexible JSON storage for all supplemental EIA attributes. |
| **Geometry** | `geom` | PostGIS LineString/MultiLineString (SRID 4326). |

---

## 4. Database Storage & Sync Strategy
To prevent duplicate records and ensure data reliability:

1.  **Source-Specific Cleanup:** Every run begins by deleting all existing records where `source = 'EIA'`. This allows for a clean "fresh start" every time the pipeline runs.
2.  **PostGIS Serialization:** Geometries are converted to **EWKT (Extended Well-Known Text)** to maintain the spatial reference ID (4326) during the database insert.
3.  **Batch Ingestion:** Data is pushed to the PostgreSQL database in **batches of 100**, ensuring optimal memory management during the transaction.

---

## 5. Value for Land Selection
This pipeline allows the platform to provide critical infrastructure insights for potential land buyers or developers:
* **Infrastructure Access:** Identify parcels with direct access to natural gas transmission for industrial use.
* **Safety & Easements:** Inform users about high-pressure pipelines crossing the property, which dictates where building construction can occur.
* **Utility Planning:** Identify the specific operators in a county to streamline utility connection requests.