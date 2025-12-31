"""
Main File of FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# from src.users.routes import user_router
from src.auth.routes import auth_router
from src.core.config import config
from src.cases.routes import cases_router
from src.jobs.apis import jobs_apis
from src.attorneys.routes import attorneys_router
from src.billings.routes import billings_router
from src.equipment_time.routes import equipment_time_router
from src.additional_documents.routes import additional_documents_router
from src.witnesses.routes import witnesses_api
from src.core.relationships import init_relationships
from src.users.apis import users_router
from src.job_assignment.apis import job_assignment_apis

app = FastAPI(
    title=config.APPLICATION_NAME,
    version=config.APPLICATION_VERSION
)

# Serve uploaded files (profile pictures, witness videos, docs, etc.)
# This enables URLs like: http://127.0.0.1:8000/uploads/...
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Default Next.js dev server
        "http://127.0.0.1:3000",  # Alternative Next.js dev server
        "http://192.168.2.53:3000"  # Your network URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # expose_headers=["Content-Disposition"]
)

init_relationships()

# Include auth router with /api prefix
app.include_router(
    auth_router,
    prefix="/api",
    tags=["authentication"]
)

app.include_router(
    users_router,
    tags=["users"]
)

app.include_router(
    cases_router,
    tags=['case']
)

app.include_router(
    jobs_apis,
    tags=['jobs']
)

app.include_router(
    witnesses_api,
    tags=['witnesses']

)
app.include_router(
    attorneys_router,
    tags=['attorneys']
)

app.include_router(
    billings_router,
    tags=['billings']
)

app.include_router(
    equipment_time_router,
    tags=['equipment-time']
)

app.include_router(
    additional_documents_router,
    tags=['additional-documents']
)

app.include_router(
    job_assignment_apis,
    tags=['job-assignment']
)

# app.include_router(
#     user_router,
#     tags=['user management']
# )