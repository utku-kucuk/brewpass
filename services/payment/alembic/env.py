from brewpass_common.migrations import run_migrations
from payment_service import models  # noqa: F401  (registers tables)
from payment_service.config import get_settings
from payment_service.db import Base

run_migrations(Base.metadata, lambda: get_settings().database_url)
