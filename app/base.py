import sqlalchemy.orm as so

# Use a registry to generate a base class
app_registry = so.registry()
Base = app_registry.generate_base()