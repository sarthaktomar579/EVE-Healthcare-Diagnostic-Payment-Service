from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.test import CentreTestOffer


class CentreBase(BaseModel):
    name: str = Field(min_length=2, max_length=255, description="Centre name")
    location: str = Field(min_length=2, max_length=255, description="City / Locality")
    address: Optional[str] = Field(default=None, description="Detailed physical address")
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    contact_email: Optional[str] = Field(default=None, max_length=255)


class CentreCreate(CentreBase):
    pass


class CentreUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    location: Optional[str] = Field(default=None, min_length=2, max_length=255)
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: Optional[bool] = None


class CentreOut(CentreBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CentreDetailOut(CentreOut):
    available_tests: List[CentreTestOffer] = []

    model_config = ConfigDict(from_attributes=True)


class CentreTestAssociationCreate(BaseModel):
    test_id: int = Field(gt=0, description="Diagnostic test ID to offer at this centre")
    price: Decimal = Field(gt=0, decimal_places=2, description="Price charged at this centre (INR)")
    duration_minutes: int = Field(default=30, gt=0, description="Estimated test duration in minutes")
    is_available: bool = Field(default=True, description="Whether test is currently bookable")
