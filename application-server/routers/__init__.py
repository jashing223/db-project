from fastapi import APIRouter

from . import (
    appointments,
    catalog,
    doctors,
    invoices,
    owners,
    pets,
    records,
    schedule,
)

api_router = APIRouter()

api_router.include_router(owners.router)
api_router.include_router(pets.router)
api_router.include_router(doctors.router)
api_router.include_router(schedule.router)
api_router.include_router(appointments.router)
api_router.include_router(catalog.router)
api_router.include_router(records.router)
api_router.include_router(invoices.router)
