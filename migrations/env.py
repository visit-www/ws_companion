import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import your models' Base object
from app.models import Base  # Make sure this is the correct import path for your app models

# This is the Alembic Config object, which provides access to the .ini file.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Fetch DATABASE_URL from the environment (e.g., for Heroku).
database_url = os.getenv("DATABASE_URL", "postgresql://admin:811976@localhost:5432/wscdb")

# Handle Heroku's old 'postgres://' URL prefix, replacing it with 'postgresql://'
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Set the database URL in Alembic's config
config.set_main_option("sqlalchemy.url", database_url)

# For autogenerate support, target the metadata of your models
target_metadata = Base.metadata

# Function to run migrations in 'offline' mode.
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable here as well.
    Calls to context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# Function to run migrations in 'online' mode.
def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    
    In this scenario, we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="public"  # Set the default schema to public
        )

        with context.begin_transaction():
            context.run_migrations()

# Determine whether to run migrations in online or offline mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
