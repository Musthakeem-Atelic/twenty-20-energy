import json

import requests
import geopandas as gpd
from shapely.geometry import MultiLineString

def fetch_eia_pipelines():
    url = "https://geo.dot.gov/server/rest/services/Hosted/Natural_Gas_Pipelines_US_EIA/FeatureServer/0/query"
    
    bounds = "-90.31,30.35,-80.84,36.67" 

    params = {
        "where": "1=1",
        "geometry": bounds,
        "geometryType": "esriGeometryEnvelope", 
        "inSR": "4326",
        "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*", 
        "returnGeometry": "true",
        "f": "json"
    }

    print("Fetching ALL pipeline data for TN and GA...")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if "error" in data:
            print(f"ArcGIS Error: {data['error'].get('message')}")
            return None

        features = data.get('features', [])
        rows = []
        
        for f in features:
            # Lowercase keys for consistency, but keep ALL data
            attrs = {k.lower(): v for k, v in f['attributes'].items()}
            geom_data = f.get('geometry')
            
            if geom_data and 'paths' in geom_data:
                attrs['geometry'] = MultiLineString(geom_data['paths'])
                rows.append(attrs)

        if not rows:
            print("No pipelines found in that area.")
            return None

        # Create GeoDataFrame with ALL columns preserved
        gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
        print(f"Successfully fetched {(gdf)} pipeline segments with all attributes intact.")
        
        # CHANGE 3: Standardize the names needed for your analysis scripts
        # without removing the original columns
        mapping = {
            "typepipe": "pipeline_type",
            "operator": "operator",
            "shape_leng": "length",
            "objectid": "objectid",
            "status": "status",
            "geometry": "geometry"

        }
        
        for old_col, new_col in mapping.items():
            if old_col in gdf.columns:
                gdf[new_col] = gdf[old_col]

        print(f"Success! Fetched {len(gdf)} segments with all attributes.")
        return gdf

    except Exception as e:
        print(f"Failed to connect to EIA Server: {e}")
        return None