# Technical Documentation: National Wetlands Inventory (NWI) Ingestion Pipeline

This document outlines the ingestion process for environmental protection data, specifically focusing on wetlands across Georgia and Tennessee. This data is critical for land-selection tools to identify environmental constraints and regulatory requirements.

## 1. Data Source & Context
The pipeline consumes data from the **National Wetlands Inventory (NWI)**, managed by the **U.S. Fish and Wildlife Service (USFWS)**. This is the authoritative national dataset for the characteristics, extent, and status of U.S. wetlands.

* **Live Map View:** [USFWS Wetlands Mapper](https://www.fws.gov/program/national-wetlands-inventory/wetlands-mapper)
* **Data Format:** ESRI File Geodatabase (.gdb)
* **Source Identifier:** `NWI`

---

## 2. Technical Workflow Summary
The pipeline processes high-resolution spatial data through a structured "State-by-State" ETL sequence.

### **Phase 1: Multi-Layer Geodatabase Loading**
Unlike standard flat files, NWI data is delivered in complex Geodatabases (`.gdb`). The system uses `fiona` and `geopandas` to programmatically inspect the GDB, identify the correct wetland layer (e.g., `GA_Wetlands`), and stream the records into memory.

### **Phase 2: Coordinate & Geometry Standardization**
* **Reprojection:** NWI data is often provided in NAD83 Albers (a projection optimized for the whole U.S.). To match our frontend maps and land-parcel data, the pipeline reprojects all coordinates to **EPSG:4326 (WGS 84)**.
* **MultiPolygon Normalization:** To ensure database consistency, the system detects single `Polygon` features and automatically wraps them into `MultiPolygon` objects. This allows for a unified geometry column in PostgreSQL that can handle both simple and complex, fragmented wetland areas.

### **Phase 3: Attribute Mapping & Units**
The pipeline extracts the following core information:
* **Wetland Type:** Classification (e.g., Freshwater Forested/Shrub Wetland, Lake, Riverine).
* **Classification Code:** The technical "Attribute" code used by environmental scientists to describe the water regime and soil.
* **Size (Acres):** The physical area of the wetland measured in **Acres**.

---

## 3. Data Schema & Content
The `wetland_details` table stores the environmental footprint for every identified wetland in the target states.

| Category | Attributes Captured | Details & Units |
| :--- | :--- | :--- |
| **Identification** | `external_id` | The original NWI_ID for cross-referencing. |
| **Classification** | `wetland_type` | Human-readable type (e.g., "Freshwater Pond"). |
| **Classification** | `classification_code` | Technical NWI attribute string. |
| **Physical Area** | `size_acres` | Measured in **Acres**. |
| **Spatial** | `state` | ISO code (GA or TN). |
| **Geometry** | `geom` | PostGIS MultiPolygon (SRID 4326). |

---

## 4. Database Strategy: Upsert & Sync
The pipeline handles large-scale updates using a specialized "Delete then Upsert" strategy to ensure data freshness:

1.  **State-Specific Purge:** Before inserting new data, the system deletes existing records for the specific state being processed (e.g., "Delete all TN records where source is NWI"). This prevents overlapping or stale data.
2.  **On-Conflict Resolution:** The insertion uses an `ON CONFLICT (external_id) DO UPDATE` clause. If a wetland ID already exists, the system updates the geometry and attributes rather than creating a duplicate, ensuring a clean "Single Source of Truth."
3.  **Batch Ingestion:** Because NWI layers can contain hundreds of thousands of records, the data is committed in **batches of 500** to maintain database stability and avoid transaction timeouts.

---

## 5. Value for Land Selection
Integrating NWI data allows our platform to provide critical "Environmental Due Diligence" insights:
* **Regulatory Alerts:** Automatically notify users if a land parcel contains protected wetlands.
* **Development Suitability:** Calculate the percentage of a property that is "Build-ready" versus "Environmental Buffer" zones.
* **Permitting Guidance:** Use the `classification_code` to help users understand what types of environmental permits might be required for land development.