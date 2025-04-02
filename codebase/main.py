from fastapi import FastAPI
from codebase.routers import router

app = FastAPI(title="FastAPI Example App")

app.include_router(router)