from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class DemoRecordBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="标题")
    content: str = Field(..., min_length=1, max_length=2000, description="内容")
    owner: str = Field(..., min_length=1, max_length=50, description="负责人")
    status: str = Field("draft", min_length=1, max_length=20, description="状态，例如 draft/published")


class DemoRecordCreate(DemoRecordBase):
    pass


class DemoRecordUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1, max_length=2000)
    owner: Optional[str] = Field(None, min_length=1, max_length=50)
    status: Optional[str] = Field(None, min_length=1, max_length=20)


class DemoRecordInDB(DemoRecordBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DemoRecord(DemoRecordInDB):
    pass


class DemoTableInitResponse(BaseModel):
    table_name: str
    initialized: bool
    key_point: str
