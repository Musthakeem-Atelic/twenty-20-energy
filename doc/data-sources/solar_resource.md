# Solar Resource Intelligence: Land Suitability Analysis

This document outlines the implementation strategy for integrating high-precision solar irradiance data into our land-selection platform for Georgia and Tennessee.

## 1. Understanding the Core Metrics

To determine the solar value of a land parcel, we track two primary scientific metrics. Both are measured in **$kWh/m^2/day$** (Kilowatt-hours per square meter per day), also commonly referred to as **"Peak Sun Hours."**

### **Global Horizontal Irradiance (GHI)**
GHI is the total amount of shortwave radiation received by a surface horizontal to the ground. 
* **Why it matters:** This is the most important metric for standard, fixed-tilt solar panels. It represents the "total fuel" available at a site.

### **Direct Normal Irradiance (DNI)**
DNI is the amount of solar radiation received per unit area by a surface that is always held perpendicular (or normal) to the rays that come in a straight line from the direction of the sun.
* **Why it matters:** This is critical for high-efficiency **tracking systems**. A high DNI indicates the land is suitable for premium solar installations that follow the sun's path.

---

## 2. Technical Approach: On-Demand Lazy Loading

### **The Challenge**
Storing every possible latitude/longitude coordinate for the states of Georgia and Tennessee would result in an unnecessarily massive database, most of which might never be queried.

### **The Solution: "Fetch-and-Cache" Strategy**
We utilize a **Lazy Loading** pattern to keep our infrastructure lightweight and fast:

1.  **Request:** When a user selects a land parcel, the system captures the center coordinates (Lat/Lon).
2.  **Check Local DB:** The system first queries our local database to see if this specific coordinate has been requested before.
3.  **Real-Time Fetch:** * If **found**, we serve the cached data immediately (zero latency).
    * If **not found**, we trigger a real-time call to the NREL Solar Resource API.
4.  **Sync & Store:** The new data is simultaneously sent to the user and saved to our database, ensuring that the next person to query that same spot gets an instant result.

---

## 3. Data Integration Example

### **API Request**
This request targets a specific location in Georgia using the standard Western Hemisphere coordinate system (Negative Longitude).

**Endpoint:**
`GET https://developer.nrel.gov/api/solar/solar_resource/v1.json?api_key={{YOUR_KEY}}&lat=32.1574&lon=-82.9071`

### **Structured Response**
The output provides annual and monthly averages. The monthly data is vital for showing users the seasonality of their land's energy production.

```json
{
    "metadata": {
        "sources": ["Perez-SUNY/NREL, 2012"]
    },
    "inputs": {
        "lat": "32.1574",
        "lon": "-82.9071"
    },
    "outputs": {
        "avg_dni": {
            "annual": 4.65,
            "monthly": {
                "jan": 4.14, "feb": 4.76, "mar": 5.12, "apr": 5.52, 
                "may": 5.53, "jun": 4.89, "jul": 4.72, "aug": 4.39, 
                "sep": 4.17, "oct": 4.38, "nov": 4.29, "dec": 3.96
            }
        },
        "avg_ghi": {
            "annual": 4.7,
            "monthly": {
                "jan": 2.85, "feb": 3.68, "mar": 4.76, "apr": 5.88, 
                "may": 6.54, "jun": 6.33, "jul": 6.18, "aug": 5.64, 
                "sep": 4.75, "oct": 4.0, "nov": 3.16, "dec": 2.63
            }
        }
    }
}
````

## 4. Data Clarity & Unit Interpretation

To ensure accurate site assessments, it is vital to understand how these numerical values translate into land utility:

* **Unit of Measurement:** All numerical outputs are expressed in **$kWh/m^2/day$**. This unit represents the total solar energy falling on one square meter of land during a single day.
* **Annual Average:** This is the multi-year historical mean. It is the industry-standard metric for long-term financial forecasting, determining the "Solar Grade" of a land parcel, and calculating the expected ROI for permanent installations.
* **Monthly Variability:** These values reveal the "Seasonality" of the site. 
    * **Peak Production:** In the Georgia/Tennessee region, peak values usually occur in **May and June**.
    * **The Winter Dip:** Values often drop by more than 50% in **December**. 
    * **Importance:** This granularity is essential for users who need to know if the land can sustain high energy demands during the winter months.
* **Data Reliability:** The dataset is sourced from the **NREL Physical Solar Model (PSM)**. It integrates satellite observations with atmospheric data (cloud cover, humidity, and aerosol optical depth) to provide a high-confidence historical profile of the specific coordinates provided.