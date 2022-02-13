from starlette.config import Config
from starlette.datastructures import Secret


config = Config("local.env")

PROJECT_NAME = "fastapi"
VERSION = "1.0.0"
API_PREFIX = "/api"

SECRET_KEY = config("SECRET_KEY", cast=Secret, default="example")

POSTGRES_USER = config("POSTGRES_USER", cast=str)
POSTGRES_PASSWORD = config("POSTGRES_PASSWORD", cast=Secret)
POSTGRES_SERVER = config("POSTGRES_SERVER", cast=str, default="l")
POSTGRES_PORT = config("POSTGRES_PORT", cast=str, default="5432")
POSTGRES_DB = config("POSTGRES_DB", cast=str)

DATABASE_URL = config(
  "DATABASE_URL",
  default=f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


JWT_SECRET = config("JWT_SECRET", cast=str)