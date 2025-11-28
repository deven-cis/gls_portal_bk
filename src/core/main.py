"""
Main File of FastAPI application
"""
from fastapi import FastAPI

# from src.users.routes import user_router
from src.auth.routes import auth_router
from src.core.config import config


app = FastAPI(
    title=config.APPLICATION_NAME,
    version=config.APPLICATION_VERSION
)

app.include_router(
    auth_router,
    tags=['authentication']
)

# app.include_router(
#     user_router,
#     tags=['user management']
# )