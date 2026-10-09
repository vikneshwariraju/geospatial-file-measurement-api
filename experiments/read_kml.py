import geopandas as gpd


gdf = gpd.read_file("experiments/sample.kml", driver="KML")

print("CRS:")
print(gdf.crs)

print("\nGeoDataFrame:")
print(gdf)

print("\nColumns:")
print(gdf.columns)

print("\nGeometry types:")
print(gdf.geometry.geom_type)

print("\nIndividual features:")

for index, row in gdf.iterrows():

    print("\nFeature index:", index)
    print("Name:", row["Name"])
    print("Geometry type:", row.geometry.geom_type)
    print("Geometry:", row.geometry)