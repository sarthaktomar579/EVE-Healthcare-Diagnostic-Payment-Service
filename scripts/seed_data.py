import sys
import os
from datetime import datetime, timedelta, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from decimal import Decimal
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.models.centre_test import CentreTest
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.core.security import get_password_hash
from app.core.logging import logger


def seed():
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        logger.info("Seeding initial users...")
        # 1. Seed Users
        admin = db.query(User).filter(User.email == "admin@evehealth.com").first()
        if not admin:
            admin = User(
                email="admin@evehealth.com",
                hashed_password=get_password_hash("AdminPass123!"),
                full_name="Dr. Evelyn Admin",
                phone_number="+919876543210",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)

        patient = db.query(User).filter(User.email == "patient@evehealth.com").first()
        if not patient:
            patient = User(
                email="patient@evehealth.com",
                hashed_password=get_password_hash("PatientPass123!"),
                full_name="Rahul Sharma",
                phone_number="+919811223344",
                role=UserRole.PATIENT,
                is_active=True,
            )
            db.add(patient)

        db.commit()

        # 2. Seed Diagnostic Tests Catalogue
        logger.info("Seeding diagnostic tests catalogue...")
        tests_data = [
            {
                "name": "Complete Blood Count (CBC)",
                "code": "CBC-100",
                "category": "Hematology",
                "description": "Evaluates overall health and detects conditions like anemia, infection and leukemia.",
                "preparation_instructions": "No specific fasting required.",
            },
            {
                "name": "Lipid Profile Panel",
                "code": "LIPID-200",
                "category": "Biochemistry",
                "description": "Measures total cholesterol, HDL, LDL, VLDL and triglycerides.",
                "preparation_instructions": "10-12 hours overnight fasting mandatory.",
            },
            {
                "name": "Thyroid Stimulating Hormone (TSH)",
                "code": "TSH-300",
                "category": "Endocrinology",
                "description": "Evaluates thyroid gland function.",
                "preparation_instructions": "Early morning sample preferred.",
            },
            {
                "name": "Glycated Hemoglobin (HbA1c)",
                "code": "HBA1C-400",
                "category": "Diabetes",
                "description": "Measures average blood sugar levels over the past 2-3 months.",
                "preparation_instructions": "No fasting required.",
            },
            {
                "name": "Vitamin D (25-Hydroxy)",
                "code": "VITD-500",
                "category": "Vitamins & Nutrients",
                "description": "Assesses vitamin D deficiency for bone and immune health.",
                "preparation_instructions": "No special preparation needed.",
            },
            {
                "name": "Chest X-Ray PA View",
                "code": "XRAY-600",
                "category": "Radiology",
                "description": "High-resolution digital imaging of lungs, heart, and chest wall.",
                "preparation_instructions": "Remove metallic objects, jewelry, and wear loose clothing.",
            },
        ]

        created_tests = {}
        for t_data in tests_data:
            test = db.query(DiagnosticTest).filter(DiagnosticTest.code == t_data["code"]).first()
            if not test:
                test = DiagnosticTest(**t_data, is_active=True)
                db.add(test)
                db.commit()
                db.refresh(test)
            created_tests[test.code] = test

        # 3. Seed Diagnostic Centres
        logger.info("Seeding diagnostic centres...")
        centres_data = [
            {
                "name": "EVE Diagnostics - Koramangala Hub",
                "location": "Koramangala, Bengaluru",
                "address": "Plot 42, 80 Feet Road, 4th Block, Koramangala",
                "contact_phone": "+918025530001",
                "contact_email": "koramangala@evehealth.com",
            },
            {
                "name": "EVE Healthcare Centre - Indiranagar",
                "location": "Indiranagar, Bengaluru",
                "address": "12th Main Road, HAL 2nd Stage, Indiranagar",
                "contact_phone": "+918025530002",
                "contact_email": "indiranagar@evehealth.com",
            },
            {
                "name": "EVE Diagnostic Lab - HSR Layout",
                "location": "HSR Layout, Bengaluru",
                "address": "Sector 1, 27th Main Road, HSR Layout",
                "contact_phone": "+918025530003",
                "contact_email": "hsr@evehealth.com",
            },
        ]

        created_centres = []
        for c_data in centres_data:
            centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.name == c_data["name"]).first()
            if not centre:
                centre = DiagnosticCentre(**c_data, is_active=True)
                db.add(centre)
                db.commit()
                db.refresh(centre)
            created_centres.append(centre)

        # 4. Associate Tests with Centres and set pricing
        logger.info("Configuring centre test availability and prices...")
        pricing_matrix = [
            # Centre 1 (Koramangala) offers all tests
            (created_centres[0].id, created_tests["CBC-100"].id, Decimal("350.00"), 15),
            (created_centres[0].id, created_tests["LIPID-200"].id, Decimal("650.00"), 20),
            (created_centres[0].id, created_tests["TSH-300"].id, Decimal("400.00"), 15),
            (created_centres[0].id, created_tests["HBA1C-400"].id, Decimal("500.00"), 15),
            (created_centres[0].id, created_tests["VITD-500"].id, Decimal("1200.00"), 20),
            (created_centres[0].id, created_tests["XRAY-600"].id, Decimal("700.00"), 30),
            # Centre 2 (Indiranagar)
            (created_centres[1].id, created_tests["CBC-100"].id, Decimal("380.00"), 15),
            (created_centres[1].id, created_tests["LIPID-200"].id, Decimal("690.00"), 20),
            (created_centres[1].id, created_tests["HBA1C-400"].id, Decimal("520.00"), 15),
            (created_centres[1].id, created_tests["VITD-500"].id, Decimal("1250.00"), 20),
            # Centre 3 (HSR Layout)
            (created_centres[2].id, created_tests["CBC-100"].id, Decimal("340.00"), 15),
            (created_centres[2].id, created_tests["TSH-300"].id, Decimal("390.00"), 15),
            (created_centres[2].id, created_tests["XRAY-600"].id, Decimal("650.00"), 30),
        ]

        for centre_id, test_id, price, duration in pricing_matrix:
            existing = (
                db.query(CentreTest)
                .filter(CentreTest.centre_id == centre_id, CentreTest.test_id == test_id)
                .first()
            )
            if not existing:
                assoc = CentreTest(
                    centre_id=centre_id,
                    test_id=test_id,
                    price=price,
                    duration_minutes=duration,
                    is_available=True,
                )
                db.add(assoc)

        db.commit()

        # 5. Seed Sample Bookings & Payments for demo patient
        logger.info("Seeding sample bookings and payments...")
        future_date_1 = datetime.now(timezone.utc) + timedelta(days=3, hours=2)
        future_date_2 = datetime.now(timezone.utc) + timedelta(days=5, hours=4)
        future_date_3 = datetime.now(timezone.utc) + timedelta(days=7, hours=1)

        sample_bookings_data = [
            {
                "booking_reference": "EVE-BK-CONF01",
                "patient_id": patient.id,
                "centre_id": created_centres[0].id,
                "test_id": created_tests["CBC-100"].id,
                "appointment_datetime": future_date_1,
                "amount": Decimal("350.00"),
                "status": BookingStatus.CONFIRMED,
                "notes": "Routine annual wellness checkup",
            },
            {
                "booking_reference": "EVE-BK-PEND02",
                "patient_id": patient.id,
                "centre_id": created_centres[1].id,
                "test_id": created_tests["LIPID-200"].id,
                "appointment_datetime": future_date_2,
                "amount": Decimal("690.00"),
                "status": BookingStatus.PENDING,
                "notes": "Fasting test, awaiting payment simulation",
            },
            {
                "booking_reference": "EVE-BK-CANC03",
                "patient_id": patient.id,
                "centre_id": created_centres[2].id,
                "test_id": created_tests["TSH-300"].id,
                "appointment_datetime": future_date_3,
                "amount": Decimal("390.00"),
                "status": BookingStatus.CANCELLED,
                "notes": "Thyroid check",
                "cancellation_reason": "Patient requested reschedule",
            },
        ]

        for b_data in sample_bookings_data:
            existing_b = db.query(Booking).filter(Booking.booking_reference == b_data["booking_reference"]).first()
            if not existing_b:
                b = Booking(**b_data)
                db.add(b)
                db.commit()
                db.refresh(b)

                # If confirmed, also add a corresponding Payment record
                if b.status == BookingStatus.CONFIRMED:
                    existing_p = db.query(Payment).filter(Payment.booking_id == b.id).first()
                    if not existing_p:
                        pmt = Payment(
                            transaction_reference="TXN-EVE-DEMO-001",
                            booking_id=b.id,
                            amount=b.amount,
                            currency="INR",
                            status=PaymentStatus.SUCCESS,
                            payment_method="UPI",
                            metadata_json='{"gateway": "simulated", "demo": true}',
                        )
                        db.add(pmt)
                        db.commit()

        logger.info("Successfully seeded database with users, centres, tests, prices, and sample bookings!")
        print("Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Seeding failed: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
