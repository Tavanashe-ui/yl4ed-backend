# alembic/env.py
import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.db.database import Base, engine

target_metadata = Base.metadata

# 1. Add your project root to the Python path so Alembic can find your 'app' folder
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 2. Import your settings and your Base models
from app.core.config import settings
from app.db.database import Base
# IMPORTANT: Import your models file so Alembic actually sees the tables!
from app.db import models 

# 3. Read the Alembic config file
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 4. Dynamically set the database URL using your FastAPI settings (this handles port 5433)
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

# 5. Tell Alembic to look at your SQLAlchemy Base metadata
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()