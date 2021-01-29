from backend.database.config import SessionLocal

# Common db dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()