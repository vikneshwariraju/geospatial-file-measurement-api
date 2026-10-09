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