import geopandas as gpd
import fiona

def fetch_wetlands(gdb_path: str, layer: str = 'TN_Wetlands') -> gpd.GeoDataFrame:
    print(f"Loading layer '{layer}' from {gdb_path}...")
    available = fiona.listlayers(gdb_path)
    print(f"  Available layers: {available}")

    if layer not in available:
        raise ValueError(f"Layer '{layer}' not found. Available: {available}")

    gdf = gpd.read_file(gdb_path, layer=layer, driver='OpenFileGDB')
    print(f"  → {len(gdf)} records loaded. CRS: {gdf.crs}")
    return gdf