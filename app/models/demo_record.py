from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.database import Base


class DemoRecordModel(Base):
    __tablename__ = "demo_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    owner = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
