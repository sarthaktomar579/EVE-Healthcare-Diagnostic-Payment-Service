import math
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.booking import Booking, BookingStatus
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.models.centre_test import CentreTest
from app.models.user import User, UserRole
from app.schemas.booking import BookingCreate, BookingCancel, BookingOut, BookingListOut
from app.schemas.common import PaginatedResponse
from app.core.logging import logger


class BookingService:
    @staticmethod
    def _to_booking_out(booking: Booking) -> BookingOut:
        return BookingOut(
            id=booking.id,
            booking_reference=booking.booking_reference,
            patient_id=booking.patient_id,
            patient_name=booking.patient.full_name if booking.patient else "Unknown",
            patient_email=booking.patient.email if booking.patient else "unknown@eve.local",
            centre_id=booking.centre_id,
            centre_name=booking.centre.name if booking.centre else "Unknown",
            centre_location=booking.centre.location if booking.centre else "Unknown",
            test_id=booking.test_id,
            test_name=booking.test.name if booking.test else "Unknown",
            test_code=booking.test.code if booking.test else "Unknown",
            appointment_datetime=booking.appointment_datetime,
            amount=booking.amount,
            status=booking.status,
            notes=booking.notes,
            cancellation_reason=booking.cancellation_reason,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
        )

    @classmethod
    def create_booking(
        cls,
        db: Session,
        patient: User,
        booking_in: BookingCreate,
    ) -> BookingOut:
        # 1. Verify centre exists and is active
        centre = db.query(DiagnosticCentre).filter(
            DiagnosticCentre.id == booking_in.centre_id,
            DiagnosticCentre.is_active == True,
        ).first()
        if not centre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic centre with ID {booking_in.centre_id} not found or inactive",
            )

        # 2. Verify test exists and is active
        test = db.query(DiagnosticTest).filter(
            DiagnosticTest.id == booking_in.test_id,
            DiagnosticTest.is_active == True,
        ).first()
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic test with ID {booking_in.test_id} not found or inactive",
            )

        # 3. Verify centre offers this specific test
        centre_test = db.query(CentreTest).filter(
            CentreTest.centre_id == booking_in.centre_id,
            CentreTest.test_id == booking_in.test_id,
        ).first()
        if not centre_test:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Diagnostic test '{test.name}' is not offered at centre '{centre.name}'",
            )

        if not centre_test.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Diagnostic test '{test.name}' is currently unavailable at centre '{centre.name}'",
            )

        # 4. Create booking with authoritative price from CentreTest (prevents price tampering)
        booking = Booking(
            patient_id=patient.id,
            centre_id=centre.id,
            test_id=test.id,
            appointment_datetime=booking_in.appointment_datetime,
            amount=centre_test.price,
            status=BookingStatus.PENDING,
            notes=booking_in.notes.strip() if booking_in.notes else None,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        logger.info(
            f"Created booking {booking.booking_reference} for patient {patient.email} "
            f"(Test: {test.name}, Centre: {centre.name}, Amount: {booking.amount})"
        )
        return cls._to_booking_out(booking)

    @classmethod
    def get_booking(
        cls,
        db: Session,
        booking_id: int,
        current_user: User,
    ) -> BookingOut:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {booking_id} not found",
            )

        # Authorization: user must own booking or be ADMIN
        if current_user.role != UserRole.ADMIN and booking.patient_id != current_user.id:
            logger.warning(
                f"Unauthorized booking access attempt: user {current_user.id} tried to access booking {booking_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this booking",
            )

        return cls._to_booking_out(booking)

    @classmethod
    def list_user_bookings(
        cls,
        db: Session,
        current_user: User,
        status_filter: Optional[BookingStatus] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[BookingListOut]:
        query = db.query(Booking)

        # If not admin, restrict to user's bookings
        if current_user.role != UserRole.ADMIN:
            query = query.filter(Booking.patient_id == current_user.id)

        if status_filter:
            query = query.filter(Booking.status == status_filter)

        total = query.count()
        offset = (page - 1) * size
        bookings = (
            query.order_by(Booking.created_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )
        pages = math.ceil(total / size) if size > 0 else 1

        items = [
            BookingListOut(
                id=b.id,
                booking_reference=b.booking_reference,
                centre_name=b.centre.name if b.centre else "Unknown",
                centre_location=b.centre.location if b.centre else "Unknown",
                test_name=b.test.name if b.test else "Unknown",
                appointment_datetime=b.appointment_datetime,
                amount=b.amount,
                status=b.status,
                created_at=b.created_at,
            )
            for b in bookings
        ]

        return PaginatedResponse[BookingListOut](
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    @classmethod
    def cancel_booking(
        cls,
        db: Session,
        booking_id: int,
        cancel_in: BookingCancel,
        current_user: User,
    ) -> BookingOut:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {booking_id} not found",
            )

        # Authorization: user must own booking or be ADMIN
        if current_user.role != UserRole.ADMIN and booking.patient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this booking",
            )

        # State transition validation
        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already cancelled",
            )

        if booking.status == BookingStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a booking that has failed",
            )

        booking.status = BookingStatus.CANCELLED
        booking.cancellation_reason = cancel_in.reason
        db.commit()
        db.refresh(booking)

        logger.info(
            f"Booking {booking.booking_reference} cancelled by user {current_user.email}. Reason: {cancel_in.reason}"
        )
        return cls._to_booking_out(booking)
