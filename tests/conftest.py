import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.models.centre_test import CentreTest

# In-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(
        email="patient@evehealth.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Jane Doe",
        phone_number="+919876543210",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session: Session) -> User:
    user = User(
        email="other_patient@evehealth.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Bob Smith",
        phone_number="+919876543211",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    admin = User(
        email="admin@evehealth.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Dr. Admin",
        phone_number="+919876543299",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    token = create_access_token(subject=test_user.id, role=test_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user: User) -> dict:
    token = create_access_token(subject=other_user.id, role=other_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_centre(db_session: Session) -> DiagnosticCentre:
    centre = DiagnosticCentre(
        name="Metro Diagnostics - Koramangala",
        location="Koramangala, Bengaluru",
        address="100 Feet Road, 4th Block",
        contact_phone="+918023456789",
        contact_email="koramangala@metrodiag.in",
        is_active=True,
    )
    db_session.add(centre)
    db_session.commit()
    db_session.refresh(centre)
    return centre


@pytest.fixture
def sample_test(db_session: Session) -> DiagnosticTest:
    diag_test = DiagnosticTest(
        name="Complete Blood Count (CBC)",
        code="CBC-001",
        description="Comprehensive evaluation of red, white blood cells and platelets.",
        category="Hematology",
        preparation_instructions="No fasting required.",
        is_active=True,
    )
    db_session.add(diag_test)
    db_session.commit()
    db_session.refresh(diag_test)
    return diag_test


@pytest.fixture
def sample_centre_test(
    db_session: Session, sample_centre: DiagnosticCentre, sample_test: DiagnosticTest
) -> CentreTest:
    ct = CentreTest(
        centre_id=sample_centre.id,
        test_id=sample_test.id,
        price=450.00,
        duration_minutes=20,
        is_available=True,
    )
    db_session.add(ct)
    db_session.commit()
    db_session.refresh(ct)
    return ct
