from fastapi import FastAPI, HTTPException,  UploadFile , File
from pathlib import Path
from app.database import SessionLocal
from app.models import UploadedFile, Measurement
from app.processor import process_geospatial_file
from app.database import engine, Base
from app import models

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Geospatial File Measurement API",
    description="API for processing geospatial files and calculating measurements.",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Geospatial File Measurement API is running"
    }


@app.post("/api/files/")
async def upload_file(file: UploadFile = File(...)):

    # 1. Validate filename and extension 
    if not file.filename: 
       raise HTTPException( 
           status_code=400, 
           detail="Filename is required." ) 
    
    
    extension = Path(file.filename).suffix.lower() 

    if extension not in [".kml", ".zip"]: 
        raise HTTPException( 
            status_code=400, 
            detail="Only .kml and .zip files are supported." 
            )

    # 2. Read and validate uploaded content 
    content = await file.read() 
    if not content: 
        raise HTTPException( 
            status_code=400, 
            detail="Uploaded file is empty." )
    
    # 3. save the uploaded file
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    # Use a generated filename to avoid path traversal 
    import uuid 
    safe_filename = f"{uuid.uuid4().hex}{extension}" 
    file_path = upload_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    db = SessionLocal()
    file_record = None  # Initialize file_record to None

    try:
        # 4. Create the file record
        file_record = UploadedFile(
            filename=file.filename,
            content_type=file.content_type,
            saved_path=str(file_path),
            status="processing"
        )

        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        # 5. Process the uploaded geospatial file
        results = process_geospatial_file(file_path)

        # 6. Save CRS details
        file_record.original_crs = results["original_crs"]
        file_record.projected_crs = results["projected_crs"]

        # 7. Save every feature's measurement
        for feature in results["features"]:
            measurement = Measurement(
                file_id=file_record.id,
                feature_id=feature["feature_id"],
                name=feature["name"],
                geometry_type=feature["geometry_type"],
                measurement_type=feature["measurement_type"],
                value=feature["value"],
                unit=feature["unit"],
                status=feature["status"]
            )

            db.add(measurement)

        file_record.status = "completed"
        db.commit()
        db.refresh(file_record)

        return {
            "id": file_record.id,
            "filename": file_record.filename,
            "status": file_record.status,
            "original_crs": file_record.original_crs,
            "projected_crs": file_record.projected_crs,
            "measurements_saved": len(results["features"])
        }

    except Exception as e:
        db.rollback()

        # Record the failed processing status if possible 
        if file_record is not None: 
            try: 
                file_record.status = "failed" 
                db.commit() 
            except Exception: 
                db.rollback() 
                
        # Invalid file content should return a client error 
        raise HTTPException( 
            status_code=400, 
            detail=f"File validation or processing failed: {str(e)}" 
            )

    finally:
        db.close()
        await file.close()

    
@app.get("/api/files/{file_id}/")
def get_file(file_id: int):
    db = SessionLocal()

    try:
        file_record = (
            db.query(UploadedFile)
            .filter(UploadedFile.id == file_id)
            .first()
        )

        if file_record is None:
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )

        return {
            "id": file_record.id,
            "filename": file_record.filename,
            "status": file_record.status,
            "original_crs": file_record.original_crs,
            "projected_crs": file_record.projected_crs,
            "measurements_count": len(file_record.measurements)
        }

    finally:
        db.close()

   
@app.get("/api/files/{file_id}/measurements/")
def get_file_measurements(file_id: int):
    db = SessionLocal()

    try:
        # 1. Check whether the uploaded file exists
        file_record = (
            db.query(UploadedFile)
            .filter(UploadedFile.id == file_id)
            .first()
        )

        if file_record is None:
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )

        # 2. Get measurements belonging to this file
        measurements = (
            db.query(Measurement)
            .filter(Measurement.file_id == file_id)
            .all()
        )

        # 3. Return file details and its measurements
        return {
            "file_id": file_record.id,
            "filename": file_record.filename,
            "status": file_record.status,
            "original_crs": file_record.original_crs,
            "projected_crs": file_record.projected_crs,
            "total_features": len(measurements),
            "measurements": [
                {
                    "feature_id": item.feature_id,
                    "name": item.name,
                    "geometry_type": item.geometry_type,
                    "measurement_type": item.measurement_type,
                    "value": item.value,
                    "unit": item.unit,
                    "status": item.status
                }
                for item in measurements
            ]
        }

    finally:
        db.close()

    