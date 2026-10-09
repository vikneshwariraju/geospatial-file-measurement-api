import geopandas as gpd
from measurements import measure_geometry

def process_kml(file_path):

    # Step 1: Read the KML
    gdf = gpd.read_file(file_path, driver="KML")

    print("Original CRS:", gdf.crs)

    # Step 2: Find a suitable projected CRS
    projected_crs = gdf.estimate_utm_crs()

    print("Projected CRS:", projected_crs)

    # Step 3: Transform geometries
    projected = gdf.to_crs(projected_crs)

    # Step 4: Process every feature
    results = []

    for index, row in projected.iterrows():

        geometry = row.geometry
        measurement= measure_geometry(geometry)

        result = {
            "feature_id": index,
            "name": row["Name"],
            **measurement
        }

        results.append(result)

    return results


results = process_kml("experiments/sample.kml")

print("\nResults:")

for result in results:
    print(result)