import geopandas as gpd

def fetch_electricity_lines(geojson_path: str) -> gpd.GeoDataFrame:
    """Load electricity transmission lines from a local GeoJSON file."""
    print(f"Loading GeoJSON from {geojson_path}...")
    gdf = gpd.read_file(geojson_path)
    print(f"  → {len(gdf)} features loaded. CRS: {gdf.crs}")
    return gdf