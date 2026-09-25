from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class TestBase(BaseModel):
    name: str = Field(min_length=2, max_length=255, description="Name of the diagnostic test")
    code: str = Field(min_length=2, max_length=50, description="Unique code for the test")
    description: Optional[str] = Field(default=None, description="Detailed test description")
    category: str = Field(default="General", max_length=100, description="Test category (e.g. Pathology, Imaging)")
    preparation_instructions: Optional[str] = Field(default=None, description="Patient preparation instructions")


class TestCreate(TestBase):
    pass


class TestUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    preparation_instructions: Optional[str] = None
    is_active: Optional[bool] = None


class TestOut(TestBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CentreTestOffer(BaseModel):
    """Represents a test offered by a specific diagnostic centre with custom price"""
    id: int
    test_id: int
    name: str
    code: str
    category: str
    description: Optional[str] = None
    preparation_instructions: Optional[str] = None
    price: Decimal
    duration_minutes: int
    is_available: bool

    class Config:
        from_attributes = True
