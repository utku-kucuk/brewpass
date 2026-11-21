from auth_service import models  # noqa: F401  (registers tables)
from auth_service.config import get_settings
from auth_service.db import Base
from brewpass_common.migrations import run_migrations

run_migrations(Base.metadata, lambda: get_settings().database_url)
