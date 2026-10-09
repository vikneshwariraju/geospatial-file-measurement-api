
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    saved_path = Column(String, nullable=False)

    original_crs = Column(String, nullable=True)
    projected_crs = Column(String, nullable=True)

    status = Column(String, default="processing")
    created_at = Column(DateTime, default=datetime.utcnow)

    measurements = relationship(
        "Measurement",
        back_populates="uploaded_file",
        cascade="all, delete-orphan"
    )


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(
        Integer,
        ForeignKey("uploaded_files.id"),
        nullable=False
    )

    feature_id = Column(Integer, nullable=False)
    name = Column(String, nullable=True)
    geometry_type = Column(String, nullable=False)

    measurement_type = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)

    status = Column(String, default="success")

    uploaded_file = relationship(
        "UploadedFile",
        back_populates="measurements"
    )