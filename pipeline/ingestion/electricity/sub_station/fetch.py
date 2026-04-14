import geopandas as gpd

def fetch_substations(geojson_path: str) -> gpd.GeoDataFrame:
    print(f"Loading substation GeoJSON from {geojson_path}...")
    gdf = gpd.read_file(geojson_path)
    print(f"  → {len(gdf)} features loaded. CRS: {gdf.crs}")
    return gdf