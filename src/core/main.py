"""
Main File of FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.auth import auth_router
from src.core.config import config
from src.cases import cases_router
from src.jobs import jobs_apis
from src.attorneys import attorneys_router
from src.billings import billings_router
from src.equipment_time import equipment_time_router
from src.witnesses import witnesses_api
from src.users import users_router
from src.job_assignment import job_assignment_apis

app = FastAPI(
    title=config.APPLICATION_NAME,
    version=config.APPLICATION_VERSION
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  
        "http://127.0.0.1:3000", 
        "http://192.168.2.53:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_router,
    prefix="/api",
    tags=["authentication"]
)

app.include_router(
    users_router,
    prefix="/api",
    tags=["users"]
)

app.include_router(
    cases_router,
    prefix="/api",
    tags=['case']
)

app.include_router(
    jobs_apis,
    prefix="/api",
    tags=['jobs']
)

app.include_router(
    witnesses_api,
    prefix="/api",
    tags=['witnesses']

)
app.include_router(
    attorneys_router,
    prefix="/api",
    tags=['attorneys']
)

app.include_router(
    billings_router,
    prefix="/api",
    tags=['billings']
)

app.include_router(
    equipment_time_router,
    prefix="/api",
    tags=['equipment-time']
)

app.include_router(
    job_assignment_apis,
    prefix="/api",
    tags=['job-assignment']
)
