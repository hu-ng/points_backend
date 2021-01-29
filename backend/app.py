from fastapi import FastAPI
from .routers import user, transaction

from backend.database.config import engine, Base

Base.metadata.create_all(bind=engine)

# Create the main app
app = FastAPI()

# Include the routers for different resources
app.include_router(user.router)
app.include_router(transaction.router)

@app.get("/")
async def root():
    return {"message": "this is a backend service"}
