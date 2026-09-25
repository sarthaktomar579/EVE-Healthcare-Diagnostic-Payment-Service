from fastapi import APIRouter
from app.api.v1.endpoints import auth, centres, tests, bookings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(centres.router)
api_router.include_router(tests.router)
api_router.include_router(bookings.router)
