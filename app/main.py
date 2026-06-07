from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.db.database import SessionLocal, engine, Base
from app.db.models import User
from app.core.security import get_password_hash
from app.db.seed import seed_geography_data
from app.middleware.audit_middleware import AuditContextMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed provinces and districts
        seed_geography_data(db)

        # Seed admin user if missing
        admin_email = "admin@yl4ed.org"
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            print("Seeding initial admin user...")
            hashed_password = get_password_hash("securepassword123"[:72])
            new_admin = User(email=admin_email, hashed_password=hashed_password, is_admin=True)
            db.add(new_admin)
            db.commit()
            print("Admin user seeded successfully.")
    finally:
        db.close()

    yield


# 1. Create FastAPI app FIRST
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# 2. Add CORS middleware
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Add audit context middleware (this sets IP & user-agent for logging)
app.add_middleware(AuditContextMiddleware)

# 4. Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to the YL4ED API. Access the docs at /docs"}