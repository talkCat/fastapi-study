from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import UserModel
from app.schemas.user import UserCreate, UserUpdate, UserRole
from app.db.repository import RepositoryBase
from app.core.security import get_password_hash, verify_password


class UserRepository(RepositoryBase):
    def __init__(self):
        super().__init__(UserModel)

    def get_by_username(self, db: Session, username: str) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.username == username).first()

    def get_by_email(self, db: Session, email: str) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.email == email).first()

    def create(self, db: Session, user_in: UserCreate) -> UserModel:
        user_data = user_in.model_dump()
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
        return super().create(db, user_data)

    def update(self, db: Session, id: int, user_in: UserUpdate) -> Optional[UserModel]:
        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        return super().update(db, id, update_data)

    def authenticate(self, db: Session, username: str, password: str) -> Optional[UserModel]:
        user = self.get_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


user_repository = UserRepository()