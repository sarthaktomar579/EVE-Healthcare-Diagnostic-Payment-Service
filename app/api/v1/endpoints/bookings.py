from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.booking import BookingStatus
from app.schemas.booking import BookingCreate, BookingCancel, BookingOut, BookingListOut
from app.schemas.common import PaginatedResponse
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "/",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Book a diagnostic test",
    description="Creates a new diagnostic test booking in PENDING status. Price is securely determined by centre catalogue.",
)
def create_booking(
    booking_in: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BookingService.create_booking(
        db=db,
        patient=current_user,
        booking_in=booking_in,
    )


@router.get(
    "/",
    response_model=PaginatedResponse[BookingListOut],
    summary="List bookings",
    description="Returns a paginated list of bookings. Patients see their own bookings; Admins can see all bookings.",
)
def list_bookings(
    status_filter: Optional[BookingStatus] = Query(None, alias="status", description="Filter by booking status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BookingService.list_user_bookings(
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        page=page,
        size=size,
    )


@router.get(
    "/{booking_id}",
    response_model=BookingOut,
    summary="Get booking details",
    description="Retrieves full details of a specific booking. Enforces authorization checks.",
)
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BookingService.get_booking(
        db=db,
        booking_id=booking_id,
        current_user=current_user,
    )


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingOut,
    summary="Cancel a booking",
    description="Cancels a PENDING or CONFIRMED booking. FAILED or CANCELLED bookings cannot be cancelled.",
)
def cancel_booking(
    booking_id: int,
    cancel_in: BookingCancel = BookingCancel(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BookingService.cancel_booking(
        db=db,
        booking_id=booking_id,
        cancel_in=cancel_in,
        current_user=current_user,
    )
