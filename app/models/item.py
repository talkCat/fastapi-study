from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base
from app.schemas.item import ItemCategory


class ItemModel(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    price = Column(Float, nullable=False)
    category = Column(SQLEnum(ItemCategory, values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())