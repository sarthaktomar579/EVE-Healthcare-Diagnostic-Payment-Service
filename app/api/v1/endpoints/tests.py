from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.test import TestCreate, TestOut
from app.schemas.common import PaginatedResponse
from app.services.centre_service import TestCatalogueService

router = APIRouter(prefix="/tests", tags=["Diagnostic Tests Catalogue"])


@router.get(
    "/",
    response_model=PaginatedResponse[TestOut],
    summary="List diagnostic tests in catalogue",
    description="Browse all available diagnostic tests with pagination, search, and category filtering.",
)
def list_tests(
    category: Optional[str] = Query(None, description="Filter by category (e.g., Pathology, Cardiology)"),
    search: Optional[str] = Query(None, description="Search by test name, code, or description"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
):
    return TestCatalogueService.list_tests(
        db=db,
        category=category,
        search=search,
        page=page,
        size=size,
    )


@router.post(
    "/",
    response_model=TestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add diagnostic test to catalogue",
    description="Registers a new test in the central catalogue.",
)
def create_test(
    test_in: TestCreate,
    db: Session = Depends(get_db),
):
    test = TestCatalogueService.create_test(db=db, test_in=test_in)
    return TestOut.model_validate(test)


@router.get(
    "/{test_id}",
    response_model=TestOut,
    summary="Get diagnostic test by ID",
    description="Retrieve specific diagnostic test catalogue details.",
)
def get_test_by_id(
    test_id: int,
    db: Session = Depends(get_db),
):
    test = TestCatalogueService.get_test_by_id(db=db, test_id=test_id)
    return TestOut.model_validate(test)
