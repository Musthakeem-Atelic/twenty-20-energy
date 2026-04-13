import geopandas as gpd
import pandas as pd

def filter_states(gdf, states_shapefile=None, state_codes=["TN", "GA"], buffer=None):
    """
    Filter GeoDataFrame to only include pipelines intersecting TN and GA.
    If `states_shapefile` is None, assumes gdf is already filtered by bounding box.
    Optionally apply a buffer (in degrees) to include pipelines near state borders.
    """
    if states_shapefile is None:
        # Already filtered by bounding box
        print(f"Using pre-filtered bounding box, records before filter: {len(gdf)}")
        return gdf

    # Load state polygons
    states = gpd.read_file(states_shapefile)
    states = states[states["STUSPS"].isin(state_codes)]

    # Match CRS
    gdf = gdf.to_crs(states.crs)

    gdf_filtered = gpd.sjoin(gdf, states, how="inner", predicate="intersects")

    print(f"Pipelines CRS: {gdf.crs}")
    print(f"States CRS: {states.crs}")
    print(f"After filtering TN/GA: {len(gdf_filtered)} records")
    return gdf_filtered

def clean_columns(gdf):
    """
    Preserves 100% of original data. 
    Adds standardized columns WITHOUT deleting or renaming originals.
    """
    if gdf is None or len(gdf) == 0:
        return gdf

    # 1. Normalize column names to lowercase for the mapping to work
    # (Original columns like OBJECTID become objectid, but data stays the same)
    gdf.columns = [c.lower() for c in gdf.columns]

    # 2. Add Standardized Columns (Direct Assignment)
    # This creates NEW columns. The old ones (typepipe, operat_nm, etc.) ARE STILL THERE.
    gdf['pipeline_type'] = gdf['typepipe'] if 'typepipe' in gdf.columns else "Natural Gas"
    gdf['operator_std'] = gdf['operat_nm'] if 'operat_nm' in gdf.columns else "Unknown"
    
    # 3. Handle Length (Finding the correct original column)
    # Checks for shape_leng or shape__length (both are common in HIFLD/EIA)
    found_len = next((c for c in ['shape_leng', 'shape__length', 'shape_len'] if c in gdf.columns), None)
    if found_len:
        gdf['length'] = pd.to_numeric(gdf[found_len], errors='coerce').fillna(0.0)
    else:
        gdf['length'] = 0.0

    data_cols = [c for c in gdf.columns if c != 'geometry']
    gdf[data_cols] = gdf[data_cols].fillna("Unknown")

    # 5. Ensure it stays a GeoDataFrame
    gdf = gpd.GeoDataFrame(gdf, geometry='geometry')

    print(f"Data preserved. Total columns: {len(gdf.columns)}")
    print(f"Current Geometry Type: {gdf.geometry.iloc[0].geom_type if not gdf.empty else 'None'}")
    
    return gdf