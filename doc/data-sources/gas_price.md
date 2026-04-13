# Technical Documentation: Natural Gas Market Pricing Ingestion

This document details the automated pipeline for tracking and ingesting historical and current natural gas price data, providing critical market context for land and energy asset valuation.

## 1. Data Source & Market Context
The pipeline interfaces with the **U.S. Energy Information Administration (EIA) V2 API**. It specifically targets the Natural Gas Future Contract prices, which represent the market's expectation of future gas prices at the Henry Hub—the primary pricing point for natural gas in the North American market.

* **Live Source:** [EIA Natural Gas Open Data](https://www.eia.gov/opendata/browser/natural-gas/pri/fut)
* **Data Frequency:** Daily
* **Source Identifier:** `EIA`

---

## 2. Technical Workflow Summary
The pipeline follows a "rolling window" synchronization strategy to ensure the database stays updated with the latest market shifts while maintaining data integrity.

### **Phase 1: Time-Windowed Fetching**
Instead of downloading the entire historical dataset, the system uses a **lookback window** (defaulting to the last 10 days).
* **API Logic:** The `fetch_gas_prices` function calculates a `start_date` and `end_date` based on the current system time.
* **Sorting:** Data is requested in descending order by period to ensure the most recent market closures are processed first.

### **Phase 3: Data Normalization & Validation**
Natural gas prices involve complex metadata describing the "series" and "process." The pipeline standardizes these into a structured format:
* **Price Extraction:** Values are converted to `float`. Any records containing null or non-numeric pricing (often due to market holidays) are automatically skipped.
* **Metadata Mapping:** Attributes such as `area_name`, `product_name`, and `series_description` are mapped to the schema to provide clear descriptions of what each price point represents (e.g., "Henry Hub Natural Gas Spot Price").
* **Unit Standardization:** Prices are typically tracked in **Dollars per Million Btu** ($/MMBtu$).

---

## 3. Data Schema & Content
The `natural_gas_price` table acts as a historical ledger for market trends.

| Category | Attributes Captured | Details |
| :--- | :--- | :--- |
| **Timeframe** | `period` | The specific trading date (stored as a PostgreSQL `date`). |
| **Value** | `value` | The price measured in **$/MMBtu**. |
| **Product** | `product_name` | Type of gas (e.g., "Natural Gas"). |
| **Geography** | `area_name` | The pricing hub (e.g., "U.S." or "Henry Hub"). |
| **Description** | `series_description` | Full text explaining the specific price series. |
| **Metadata** | `raw_metadata` | JSONB blob containing the complete original API response. |

---

## 4. Database Storage & Duplicate Prevention
To ensure the database does not accumulate duplicate records for the same trading days, the pipeline employs a **"Delete-before-Insert"** window strategy:

1.  **Window Cleanup:** Before inserting new records, the system identifies the exact date range covered by the current fetch (e.g., the last 10 days). It deletes any existing entries from the `EIA` source within that specific window.
2.  **Atomic Casts:** The pipeline uses explicit PostgreSQL casting for specific data types, including:
    * `cast(:period as date)` for temporal accuracy.
    * `cast(:frequency as frequencyenum)` to maintain strict data typing for "Daily" vs "Monthly" data.
    * `cast(:raw_metadata as jsonb)` for high-performance JSON querying.
3.  **Batch Ingestion:** Data is processed in small batches to ensure transaction stability and error tracking.

---

## 5. Value for Land & Energy Analysis
Tracking gas prices alongside physical land parcels and pipelines provides three major advantages:
* **Revenue Projection:** Helps landowners estimate potential royalties or income from gas production on their property based on current market rates.
* **Investment Timing:** Allows developers to track market volatility when planning new pipeline interconnections or energy-intensive facilities.
* **Economic Trends:** Provides a visual correlation between local land value and national energy price fluctuations ($/MMBtu$).