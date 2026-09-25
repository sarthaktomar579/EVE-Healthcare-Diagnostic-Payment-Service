from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.centre import (
    CentreCreate,
    CentreOut,
    CentreDetailOut,
    CentreTestAssociationCreate,
)
from app.schemas.test import CentreTestOffer
from app.schemas.common import PaginatedResponse
from app.services.centre_service import CentreService

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


@router.get(
    "/",
    response_model=PaginatedResponse[CentreOut],
    summary="List diagnostic centres",
    description="Retrieve diagnostic centres with optional search by name or location. Cached for fast response.",
)
def list_centres(
    search: Optional[str] = Query(None, description="Search term for centre name or location"),
    location: Optional[str] = Query(None, description="Filter by location / city"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
):
    return CentreService.list_centres(
        db=db,
        search=search,
        location=location,
        page=page,
        size=size,
    )


@router.post(
    "/",
    response_model=CentreOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create diagnostic centre",
    description="Registers a new diagnostic centre in the system.",
)
def create_centre(
    centre_in: CentreCreate,
    db: Session = Depends(get_db),
):
    centre = CentreService.create_centre(db=db, centre_in=centre_in)
    return CentreOut.model_validate(centre)


@router.get(
    "/{centre_id}",
    response_model=CentreDetailOut,
    summary="Get diagnostic centre details and available tests",
    description="Returns detailed information about a diagnostic centre along with its available tests and prices.",
)
def get_centre_details(
    centre_id: int,
    db: Session = Depends(get_db),
):
    return CentreService.get_centre_details(db=db, centre_id=centre_id)


@router.post(
    "/{centre_id}/tests",
    response_model=CentreTestOffer,
    status_code=status.HTTP_201_CREATED,
    summary="Offer diagnostic test at centre",
    description="Configures a test as available at a specific centre with custom pricing and duration.",
)
def associate_test_with_centre(
    centre_id: int,
    assoc_in: CentreTestAssociationCreate,
    db: Session = Depends(get_db),
):
    ct = CentreService.associate_test(db=db, centre_id=centre_id, assoc_in=assoc_in)
    return CentreTestOffer(
        id=ct.id,
        test_id=ct.test.id,
        name=ct.test.name,
        code=ct.test.code,
        category=ct.test.category,
        description=ct.test.description,
        preparation_instructions=ct.test.preparation_instructions,
        price=ct.price,
        duration_minutes=ct.duration_minutes,
        is_available=ct.is_available,
    )
