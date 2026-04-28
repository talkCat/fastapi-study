from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.item import ItemModel
from app.schemas.item import ItemCreate, ItemUpdate, ItemCategory
from app.db.repository import RepositoryBase


class ItemRepository(RepositoryBase):
    def __init__(self):
        super().__init__(ItemModel)

    def get_by_name(self, db: Session, name: str) -> Optional[ItemModel]:
        return db.query(ItemModel).filter(ItemModel.name == name).first()

    def get_by_owner(self, db: Session, owner_id: int, skip: int = 0, limit: int = 100) -> List[ItemModel]:
        return db.query(ItemModel).filter(ItemModel.owner_id == owner_id).offset(skip).limit(limit).all()

    def get_by_category(
        self, db: Session, category: ItemCategory, skip: int = 0, limit: int = 100
    ) -> List[ItemModel]:
        return db.query(ItemModel).filter(ItemModel.category == category).offset(skip).limit(limit).all()

    def search(self, db: Session, keyword: str, skip: int = 0, limit: int = 100) -> List[ItemModel]:
        return (
            db.query(ItemModel)
            .filter(or_(ItemModel.name.ilike(f"%{keyword}%"), ItemModel.description.ilike(f"%{keyword}%")))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db: Session, item_in: ItemCreate, owner_id: int) -> ItemModel:
        item_data = item_in.model_dump()
        item_data["owner_id"] = owner_id
        return super().create(db, item_data)


item_repository = ItemRepository()