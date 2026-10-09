import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon


point = Point(80.27, 13.08)

line = LineString([
    (80.27, 13.08),
    (80.28, 13.08),
    (80.29, 13.09)
])

polygon = Polygon([
    (80.27, 13.08),
    (80.28, 13.08),
    (80.28, 13.09),
    (80.27, 13.09)
])


gdf = gpd.GeoDataFrame(
    {
        "name": ["Location A", "Road A", "Lake A"],
        "type": ["location", "road", "lake"]
    },
    geometry=[point, line, polygon],
    crs="EPSG:4326"
)


print("Original CRS:")
print(gdf.crs)


projected_crs = gdf.estimate_utm_crs()

print("\nEstimated CRS:")
print(projected_crs)


projected = gdf.to_crs(projected_crs)

print("\nProjected CRS:")
print(projected.crs)


polygon_projected = projected.iloc[2].geometry
line_projected = projected.iloc[1].geometry


print("\nArea:", polygon_projected.area, "m²")
print("Length:", line_projected.length, "m")