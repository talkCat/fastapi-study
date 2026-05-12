from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import get_engine
from app.db.repository import RepositoryBase
from app.models.demo_record import DemoRecordModel
from app.schemas.demo_record import DemoRecordCreate, DemoRecordUpdate


class DemoRecordRepository(RepositoryBase):
    def __init__(self):
        super().__init__(DemoRecordModel)

    def get_by_title(self, db: Session, title: str) -> Optional[DemoRecordModel]:
        return db.query(DemoRecordModel).filter(DemoRecordModel.title == title).first()

    def create(self, db: Session, demo_in: DemoRecordCreate) -> DemoRecordModel:
        return super().create(db, demo_in.model_dump())

    def update(self, db: Session, id: int, demo_in: DemoRecordUpdate) -> Optional[DemoRecordModel]:
        return super().update(db, id, demo_in.model_dump(exclude_unset=True))


class DemoRecordService:
    def __init__(self, repository: DemoRecordRepository):
        self.repository = repository

    def init_table(self) -> None:
        DemoRecordModel.__table__.create(bind=get_engine(), checkfirst=True)

    def list_records(self, db: Session, skip: int = 0, limit: int = 20):
        return self.repository.get_all(db, skip=skip, limit=limit)

    def get_record(self, db: Session, record_id: int):
        return self.repository.get(db, record_id)

    def create_record(self, db: Session, demo_in: DemoRecordCreate):
        return self.repository.create(db, demo_in)

    def update_record(self, db: Session, record_id: int, demo_in: DemoRecordUpdate):
        return self.repository.update(db, record_id, demo_in)

    def delete_record(self, db: Session, record_id: int) -> bool:
        return self.repository.delete(db, record_id)


demo_record_repository = DemoRecordRepository()
demo_record_service = DemoRecordService(demo_record_repository)
