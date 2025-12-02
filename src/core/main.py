"""
Main File of FastAPI application
"""
from fastapi import FastAPI

# from src.users.routes import user_router
from src.auth.routes import auth_router
from src.core.config import config
from src.cases.routes import cases_router
from src.jobs.routes import jobs_router


app = FastAPI(
    title=config.APPLICATION_NAME,
    version=config.APPLICATION_VERSION
)

app.include_router(
    auth_router,
    tags=['authentication']
)

app.include_router(
    cases_router,
    tags=['cases']
)

app.include_router(
    jobs_router,
    tags=['jobs']
)

# app.include_router(
#     user_router,
#     tags=['user management']
# )