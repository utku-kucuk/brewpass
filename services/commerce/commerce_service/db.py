from brewpass_common.db import DeclarativeBase, SessionFactory, new_metadata
from commerce_service.config import get_settings


class Base(DeclarativeBase):
    metadata = new_metadata()


SessionLocal = SessionFactory(lambda: get_settings().database_url)
get_db = SessionLocal.get_db
