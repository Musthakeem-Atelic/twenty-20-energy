import os
import geopandas as gpd
import fiona

# Paths
BASE_DIR = os.getcwd()

GPKG_PATH = os.path.join(
    BASE_DIR,
    "data",
    "wetland",
    "GA_geopackage_wetlands.gpkg"
)

# 1. List layers (important for GPKG)
layers = fiona.listlayers(GPKG_PATH)
print("Layers:", layers)

# 2. Load first layer
gdf = gpd.read_file(GPKG_PATH, layer=layers[3])

# 3. Print few rows
print("\n--- FIRST 5 ROWS ---")
print(gdf.head())

# 4. Optional: show only selected columns (clean view)
print("\n--- SELECTED VIEW ---")
print(gdf.head()[gdf.columns[:5]])  # first 5 columns