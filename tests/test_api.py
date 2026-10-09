"""API and geometry tests for the Geospatial File Measurement API.

Run from the project root with: python -m pytest -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from shapely.geometry import LineString, Point, Polygon

from app import main
from app.database import Base
from app.models import Measurement, UploadedFile
from app.processor import measure_geometry


@pytest.fixture()
def client_and_db(monkeypatch):
    """Use an isolated in-memory SQLite database for each test."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)
    monkeypatch.setattr(main, "SessionLocal", TestingSessionLocal)

    with TestClient(main.app) as test_client:
        yield test_client, TestingSessionLocal

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def sample_processing_result():
    """Deterministic result returned by the mocked file processor."""
    return {
        "original_crs": "EPSG:4326",
        "projected_crs": "EPSG:32644",
        "features": [
            {
                "feature_id": 0,
                "name": "Location A",
                "geometry_type": "Point",
                "measurement_type": None,
                "value": None,
                "unit": None,
                "status": "success",
            },
            {
                "feature_id": 1,
                "name": "Road A",
                "geometry_type": "LineString",
                "measurement_type": "length",
                "value": 123.5,
                "unit": "m",
                "status": "success",
            },
            {
                "feature_id": 2,
                "name": "Lake A",
                "geometry_type": "Polygon",
                "measurement_type": "area",
                "value": 456.75,
                "unit": "m²",
                "status": "success",
            },
        ],
    }


def test_upload_kml_saves_file_and_measurements(client_and_db, monkeypatch):
    client, SessionLocal = client_and_db
    monkeypatch.setattr(
        main, "process_geospatial_file", lambda _path: sample_processing_result()
    )

    response = client.post(
        "/api/files/",
        files={"file": ("sample.kml", b"non-empty test content", "application/vnd.google-earth.kml+xml")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["filename"] == "sample.kml"
    assert payload["status"] == "completed"
    assert payload["original_crs"] == "EPSG:4326"
    assert payload["projected_crs"] == "EPSG:32644"
    assert payload["measurements_saved"] == 3

    db = SessionLocal()
    try:
        saved_file = db.query(UploadedFile).filter_by(id=payload["id"]).one()
        saved_measurements = (
            db.query(Measurement).filter_by(file_id=payload["id"]).all()
        )
        assert saved_file.status == "completed"
        assert len(saved_measurements) == 3
    finally:
        db.close()


def test_unsupported_extension_is_rejected(client_and_db):
    client, _ = client_and_db
    response = client.post(
        "/api/files/",
        files={"file": ("notes.txt", b"some text", "text/plain")},
    )
    assert response.status_code == 400
    assert "Only .kml and .zip" in response.json()["detail"]


def test_empty_upload_is_rejected(client_and_db):
    client, _ = client_and_db
    response = client.post(
        "/api/files/",
        files={"file": ("empty.kml", b"", "application/vnd.google-earth.kml+xml")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_processing_error_marks_file_failed(client_and_db, monkeypatch):
    client, SessionLocal = client_and_db

    def fail_processing(_path):
        raise ValueError("ZIP archive does not contain a Shapefile (.shp).")

    monkeypatch.setattr(main, "process_geospatial_file", fail_processing)
    response = client.post(
        "/api/files/",
        files={"file": ("no_shapefile.zip", b"not-empty", "application/zip")},
    )

    assert response.status_code == 400
    assert "does not contain a Shapefile" in response.json()["detail"]
    db = SessionLocal()
    try:
        saved_file = db.query(UploadedFile).filter_by(filename="no_shapefile.zip").one()
        assert saved_file.status == "failed"
    finally:
        db.close()


def test_get_file_details(client_and_db, monkeypatch):
    client, _ = client_and_db
    monkeypatch.setattr(
        main, "process_geospatial_file", lambda _path: sample_processing_result()
    )
    upload = client.post(
        "/api/files/",
        files={"file": ("sample.kml", b"content", "application/vnd.google-earth.kml+xml")},
    )
    file_id = upload.json()["id"]

    response = client.get(f"/api/files/{file_id}/")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] == file_id
    assert payload["status"] == "completed"
    assert payload["measurements_count"] == 3


def test_get_measurements_returns_all_geometry_types(client_and_db, monkeypatch):
    client, _ = client_and_db
    monkeypatch.setattr(
        main, "process_geospatial_file", lambda _path: sample_processing_result()
    )
    upload = client.post(
        "/api/files/",
        files={"file": ("sample.kml", b"content", "application/vnd.google-earth.kml+xml")},
    )
    file_id = upload.json()["id"]

    response = client.get(f"/api/files/{file_id}/measurements/")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["file_id"] == file_id
    assert payload["total_features"] == 3
    by_type = {item["geometry_type"]: item for item in payload["measurements"]}
    assert by_type["Point"]["value"] is None
    assert by_type["LineString"]["measurement_type"] == "length"
    assert by_type["LineString"]["unit"] == "m"
    assert by_type["Polygon"]["measurement_type"] == "area"
    assert by_type["Polygon"]["unit"] == "m²"


def test_missing_file_returns_404(client_and_db):
    client, _ = client_and_db
    response = client.get("/api/files/999999/")
    assert response.status_code == 404


def test_measure_geometry_for_point_has_no_measurement():
    result = measure_geometry(Point(10, 20))
    assert result["geometry_type"] == "Point"
    assert result["measurement_type"] is None
    assert result["value"] is None
    assert result["unit"] is None
    assert result["status"] == "success"


def test_measure_geometry_for_linestring_returns_length():
    result = measure_geometry(LineString([(0, 0), (3, 4)]))
    assert result["geometry_type"] == "LineString"
    assert result["measurement_type"] == "length"
    assert result["value"] == pytest.approx(5.0)
    assert result["unit"] == "m"


def test_measure_geometry_for_polygon_returns_area():
    result = measure_geometry(
        Polygon([(0, 0), (4, 0), (4, 3), (0, 3), (0, 0)])
    )
    assert result["geometry_type"] == "Polygon"
    assert result["measurement_type"] == "area"
    assert result["value"] == pytest.approx(12.0)
    assert result["unit"] == "m²"


def test_unsupported_geometry_is_marked_unsupported():
    result = measure_geometry(
        # MultiPoint is intentionally outside the currently supported measurement types.
        __import__("shapely.geometry", fromlist=["MultiPoint"]).MultiPoint([(0, 0), (1, 1)])
    )
    assert result["geometry_type"] == "MultiPoint"
    assert result["measurement_type"] is None
    assert result["value"] is None
    assert result["status"] == "unsupported"
