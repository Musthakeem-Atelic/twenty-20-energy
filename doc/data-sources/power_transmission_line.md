# Technical Documentation: Power Transmission Line Ingestion Pipeline

This document outlines the automated ETL (Extract, Transform, Load) process for integrating high-voltage power infrastructure data into our spatial database, specifically targeting the Georgia and Tennessee regions.

## 1. Data Source & Live Connectivity
We leverage the **HIFLD (Homeland Infrastructure Foundation-Level Data)** "Electric Power Transmission Lines" dataset. This is the primary federal source for open-source grid infrastructure data.

* **Live Map Explorer:** [HIFLD Electric Power Transmission Lines](https://www.arcgis.com/apps/mapviewer/index.html?layers=d4090758322c4d32a4cd002ffaa0aa12)
* **Data Type:** Vector LineString (Geographic Information System data).

---

## 2. Ingestion Workflow
The pipeline is designed to be idempotent and precise, ensuring that only the highest quality spatial data reaches our production environment.

### **Phase 1: Fetching & Standardization**
The process begins by loading the raw GeoJSON source file. Because coordinate precision is critical for land-selection tools, the system automatically checks the Coordinate Reference System (CRS). If the data is not in **EPSG:4326 (WGS 84)**, it is reprojected to ensure perfect alignment with our global map layers and GPS coordinates.

### **Phase 2: State-Level Spatial Filtering**
To maintain a high-performance database, we do not store the entire U.S. grid. We apply a **Spatial Intersection Filter**:
1.  The system loads official US Census state boundaries for **Georgia (GA)** and **Tennessee (TN)**.
2.  A **Spatial Join (`sjoin`)** is executed. Only transmission lines that physically intersect with the state polygons of GA and TN are retained.
3.  During this intersection, the system enriches the data by attaching official State ISO codes (`STUSPS`) and names to each line record.

### **Phase 3: Data Integrity & Cleaning**
Before moving to storage, the data undergoes several validation checks:
* **Geometry Validation:** Any "ghost features" (records with empty or null geometries) are purged to prevent rendering errors on the frontend.
* **Unit Normalization:** * **Voltage:** Measured and stored in **kV (Kilovolts)**.
    * **Null Handling:** Specific placeholder values (like `-999999`) are converted to `null` to prevent skewed data analysis.
* **Column Mapping:** Raw HIFLD attributes (e.g., `SUB_1`, `VOLT_CLASS`) are mapped to our standardized internal schema.

---

## 3. Data Schema & Content
The final database records provide a comprehensive technical profile of the local grid infrastructure.

| Category | Attributes Captured | Details & Units |
| :--- | :--- | :--- |
| **Identification** | Unique Line ID, Source (HIFLD), State ISO, State Name | Primary keys for indexing. |
| **Technical** | Operating Voltage (**kV**) | Numerical capacity of the line. |
| **Technical** | Voltage Class | Categorical grouping (e.g., 100-161kV). |
| **Operational** | Owner/Utility Name | Entity responsible (e.g., Georgia Power). |
| **Operational** | Operational Status | Current state (In Service, Proposed, Retired). |
| **Connectivity** | Associated Substation 1 & 2 | Connecting points for the circuit. |
| **Metadata** | `raw_metadata` (JSONB) | 100% of original source data preserved. |

---

## 4. Storage & Synchronization Strategy
To ensure the database remains a "Single Source of Truth" without stale data:

1.  **Atomic Deletion:** The pipeline identifies all existing records in the `electricity_transmission_line` table where the source is marked as `HIFLD` and deletes them before re-insertion.
2.  **PostGIS Integration:** Geometries are converted to **EWKT (Extended Well-Known Text)** and inserted using the `ST_GeomFromEWKT` function with **SRID 4326**.
3.  **Batch Processing:** Data is inserted in batches of 100. This minimizes database overhead and ensures high-speed ingestion even for large datasets.

---

## 5. Value for Land Selection
By processing the transmission lines this way, our platform can instantly answer critical land-use questions:
* **Proximity:** Distance from the land parcel to the nearest high-voltage line.
* **Capacity:** The voltage capacity (**kV**) available for heavy industrial or solar interconnection.
* **Utility Provider:** Identification of the utility owner to facilitate easement or connection inquiries.