"""FastAPI entry point — mount API routes and enable CORS for the front-end."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(title="Pet Hospital API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
