from brewpass_common.migrations import run_migrations
from commerce_service import models  # noqa: F401  (registers tables)
from commerce_service.config import get_settings
from commerce_service.db import Base

run_migrations(Base.metadata, lambda: get_settings().database_url)
