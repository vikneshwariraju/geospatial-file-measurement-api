import geopandas as gpd
import zipfile


def measure_geometry(geometry):
    if geometry.geom_type == "Polygon":
        return {
            "geometry_type": "Polygon",
            "measurement_type": "area",
            "value": geometry.area,
            "unit": "m²",
            "status": "success"
        }

    elif geometry.geom_type == "LineString":
        return {
            "geometry_type": "LineString",
            "measurement_type": "length",
            "value": geometry.length,
            "unit": "m",
            "status": "success"
        }

    elif geometry.geom_type == "Point":
        return {
            "geometry_type": "Point",
            "measurement_type": None,
            "value": None,
            "unit": None,
            "status": "success"
        }

    else:
        return {
            "geometry_type": geometry.geom_type,
            "measurement_type": None,
            "value": None,
            "unit": None,
            "status": "unsupported"
        }


def process_geospatial_file(file_path):
    file_path = str(file_path)

    if file_path.lower().endswith(".kml"):
        gdf = gpd.read_file(file_path, driver="KML")

    elif file_path.lower().endswith(".zip"):
        if not zipfile.is_zipfile(file_path):
            raise ValueError("Uploaded ZIP file is invalid.")

        with zipfile.ZipFile(file_path) as archive:
            shp_files = [
                name for name in archive.namelist()
                if name.lower().endswith(".shp")
                and not name.startswith("__MACOSX/")
            ]

        if not shp_files:
            raise ValueError(
                "ZIP archive does not contain a Shapefile (.shp)."
            )

        if len(shp_files) > 1:
            raise ValueError(
                "ZIP archive contains multiple Shapefiles. "
                "Please upload one Shapefile per ZIP."
            )

        gdf = gpd.read_file(
            f"zip://{file_path}!{shp_files[0]}"
        )

    else:
        raise ValueError("Unsupported file format.")

    if gdf.empty:
        raise ValueError("No features found in the file.")

    if gdf.crs is None:
        raise ValueError("File is missing its coordinate reference system (CRS).")

    original_crs = gdf.crs
    projected_crs = gdf.estimate_utm_crs()

    if projected_crs is None:
        raise ValueError("Could not determine a suitable projected CRS.")

    projected = gdf.to_crs(projected_crs)

    results = []

    for index, row in projected.iterrows():
        geometry = row.geometry

        if geometry is None or geometry.is_empty:
            measurement = {
                "geometry_type": "Unknown",
                "measurement_type": None,
                "value": None,
                "unit": None,
                "status": "unsupported"
            }
        else:
            measurement = measure_geometry(geometry)

        name = row.get("Name", row.get("name", None))

        results.append({
            "feature_id": int(index),
            "name": name,
            **measurement
        })

    return {
        "original_crs": str(original_crs),
        "projected_crs": str(projected_crs),
        "features": results
    }

