import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon


def filter_states(gdf, states_shapefile=None, state_codes=["TN", "GA"], buffer=None):
    """
    Spatially filter records by state polygons.
    Attaches state fields (STUSPS, NAME) from shapefile.
    """
    if states_shapefile is None:
        print(f"Using pre-filtered bounding box, records before filter: {len(gdf)}")
        return gdf

    states = gpd.read_file(states_shapefile)
    states = states[states["STUSPS"].isin(state_codes)]

    # Match CRS
    gdf = gdf.to_crs(states.crs)

    # Optional buffer
    if buffer:
        states = states.copy()
        states["geometry"] = states.geometry.buffer(buffer)

    gdf_filtered = gpd.sjoin(gdf, states, how="inner", predicate="intersects")

    print(f"Pipelines CRS: {gdf.crs}")
    print(f"States CRS: {states.crs}")
    print(f"After filtering states {state_codes}: {len(gdf_filtered)} records")

    return gdf_filtered


def to_voltage(val):
    """
    Parse voltage:
    - '161000' → 161000.0
    - '161000;115000' → 161000.0
    """
    if val is None:
        return None

    val = str(val).strip()

    if not val:
        return None

    primary = val.split(";")[0].strip()

    try:
        return float(primary)
    except ValueError:
        return None


def normalize_geometry(geom):
    """
    Ensure geometry is MULTIPOLYGON:
    - Polygon      → MultiPolygon
    - MultiPolygon → keep
    - others       → None
    """
    if geom is None or geom.is_empty:
        return None

    if isinstance(geom, Polygon):
        return MultiPolygon([geom])

    if isinstance(geom, MultiPolygon):
        return geom

    return None


def clean_substations(gdf, states_shapefile):
    """
    Full cleaning pipeline:
    - CRS normalize
    - spatial filter
    - voltage parse
    - geometry normalize
    """
    if gdf is None or len(gdf) == 0:
        return gdf

    # Ensure CRS
    if gdf.crs is None:
        print("Setting CRS to EPSG:4326...")
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        print("Reprojecting to EPSG:4326...")
        gdf = gdf.to_crs("EPSG:4326")

    # Spatial filter
    print("Filtering to TN/GA...")
    gdf = filter_states(gdf, states_shapefile)
    print(f"  → {len(gdf)} records after spatial filter")

    # Voltage
    if "voltage_raw" in gdf.columns:
        gdf["voltage"] = gdf["voltage_raw"].apply(to_voltage)
    else:
        gdf["voltage"] = None

    # Geometry normalize
    print("Normalizing geometries...")
    gdf["geom_clean"] = gdf.geometry.apply(normalize_geometry)

    bad = gdf["geom_clean"].isna()

    if bad.sum():
        print(
            f"⚠️ Dropping {bad.sum()} invalid rows "
            f"({gdf[bad].geometry.geom_type.value_counts().to_dict()})"
        )
        gdf = gdf[~bad].copy()

    gdf = gdf.set_geometry("geom_clean")

    print(f"  → {len(gdf)} valid records")
    print("Geometry types:")
    print(gdf.geometry.geom_type.value_counts().to_string())

    return gdf