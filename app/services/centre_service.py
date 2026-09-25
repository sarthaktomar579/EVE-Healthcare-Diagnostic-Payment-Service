import math
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.models.centre_test import CentreTest
from app.schemas.centre import (
    CentreCreate,
    CentreUpdate,
    CentreDetailOut,
    CentreTestAssociationCreate,
    CentreOut,
)
from app.schemas.test import TestCreate, TestOut, CentreTestOffer
from app.schemas.common import PaginatedResponse
from app.core.redis import cache
from app.core.logging import logger


class CentreService:
    CACHE_KEY_PREFIX = "eve:centres:"

    @classmethod
    def list_centres(
        cls,
        db: Session,
        search: Optional[str] = None,
        location: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[CentreOut]:
        cache_key = f"{cls.CACHE_KEY_PREFIX}list:{search}:{location}:{page}:{size}"
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for centres list: {cache_key}")
            return PaginatedResponse[CentreOut](**cached_result)

        query = db.query(DiagnosticCentre).filter(DiagnosticCentre.is_active == True)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    DiagnosticCentre.name.ilike(search_term),
                    DiagnosticCentre.location.ilike(search_term),
                )
            )

        if location:
            query = query.filter(DiagnosticCentre.location.ilike(f"%{location.strip()}%"))

        total = query.count()
        offset = (page - 1) * size
        items = query.order_by(DiagnosticCentre.name).offset(offset).limit(size).all()
        pages = math.ceil(total / size) if size > 0 else 1

        result = PaginatedResponse[CentreOut](
            items=[CentreOut.model_validate(c) for c in items],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

        # Cache for 5 minutes
        cache.set(cache_key, result.model_dump())
        return result

    @classmethod
    def get_centre_details(cls, db: Session, centre_id: int) -> CentreDetailOut:
        cache_key = f"{cls.CACHE_KEY_PREFIX}detail:{centre_id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return CentreDetailOut(**cached_result)

        centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
        if not centre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic centre with ID {centre_id} not found",
            )

        # Collect offered tests
        offers = []
        for ct in centre.centre_tests:
            if ct.is_available and ct.test and ct.test.is_active:
                offers.append(
                    CentreTestOffer(
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
                )

        detail = CentreDetailOut(
            id=centre.id,
            name=centre.name,
            location=centre.location,
            address=centre.address,
            contact_phone=centre.contact_phone,
            contact_email=centre.contact_email,
            is_active=centre.is_active,
            created_at=centre.created_at,
            updated_at=centre.updated_at,
            available_tests=offers,
        )

        cache.set(cache_key, detail.model_dump(), ttl_seconds=300)
        return detail

    @classmethod
    def create_centre(cls, db: Session, centre_in: CentreCreate) -> DiagnosticCentre:
        centre = DiagnosticCentre(
            name=centre_in.name.strip(),
            location=centre_in.location.strip(),
            address=centre_in.address.strip() if centre_in.address else None,
            contact_phone=centre_in.contact_phone.strip() if centre_in.contact_phone else None,
            contact_email=centre_in.contact_email.strip() if centre_in.contact_email else None,
            is_active=True,
        )
        db.add(centre)
        db.commit()
        db.refresh(centre)
        cache.invalidate_prefix(cls.CACHE_KEY_PREFIX)
        logger.info(f"Created diagnostic centre: {centre.name} (ID: {centre.id})")
        return centre

    @classmethod
    def associate_test(
        cls,
        db: Session,
        centre_id: int,
        assoc_in: CentreTestAssociationCreate,
    ) -> CentreTest:
        # Validate centre exists
        centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
        if not centre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic centre with ID {centre_id} not found",
            )

        # Validate test exists
        test = db.query(DiagnosticTest).filter(DiagnosticTest.id == assoc_in.test_id).first()
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic test with ID {assoc_in.test_id} not found",
            )

        # Check existing association
        existing = (
            db.query(CentreTest)
            .filter(CentreTest.centre_id == centre_id, CentreTest.test_id == assoc_in.test_id)
            .first()
        )

        if existing:
            existing.price = assoc_in.price
            existing.duration_minutes = assoc_in.duration_minutes
            existing.is_available = assoc_in.is_available
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated test association for centre {centre_id} & test {assoc_in.test_id}")
            result_ct = existing
        else:
            ct = CentreTest(
                centre_id=centre_id,
                test_id=assoc_in.test_id,
                price=assoc_in.price,
                duration_minutes=assoc_in.duration_minutes,
                is_available=assoc_in.is_available,
            )
            db.add(ct)
            db.commit()
            db.refresh(ct)
            logger.info(f"Associated test {assoc_in.test_id} to centre {centre_id}")
            result_ct = ct

        cache.invalidate_prefix(cls.CACHE_KEY_PREFIX)
        return result_ct


class TestCatalogueService:
    @staticmethod
    def list_tests(
        db: Session,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[TestOut]:
        query = db.query(DiagnosticTest).filter(DiagnosticTest.is_active == True)

        if category:
            query = query.filter(DiagnosticTest.category.ilike(f"%{category.strip()}%"))

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    DiagnosticTest.name.ilike(search_term),
                    DiagnosticTest.code.ilike(search_term),
                    DiagnosticTest.description.ilike(search_term),
                )
            )

        total = query.count()
        offset = (page - 1) * size
        items = query.order_by(DiagnosticTest.name).offset(offset).limit(size).all()
        pages = math.ceil(total / size) if size > 0 else 1

        return PaginatedResponse[TestOut](
            items=[TestOut.model_validate(t) for t in items],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    @staticmethod
    def create_test(db: Session, test_in: TestCreate) -> DiagnosticTest:
        existing = (
            db.query(DiagnosticTest)
            .filter(DiagnosticTest.code == test_in.code.strip().upper())
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Diagnostic test with code '{test_in.code}' already exists",
            )

        test = DiagnosticTest(
            name=test_in.name.strip(),
            code=test_in.code.strip().upper(),
            description=test_in.description.strip() if test_in.description else None,
            category=test_in.category.strip(),
            preparation_instructions=test_in.preparation_instructions.strip()
            if test_in.preparation_instructions
            else None,
            is_active=True,
        )
        db.add(test)
        db.commit()
        db.refresh(test)
        logger.info(f"Created diagnostic test: {test.name} ({test.code})")
        return test

    @staticmethod
    def get_test_by_id(db: Session, test_id: int) -> DiagnosticTest:
        test = db.query(DiagnosticTest).filter(DiagnosticTest.id == test_id).first()
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic test with ID {test_id} not found",
            )
        return test
