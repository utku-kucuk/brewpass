from geoalchemy2 import alembic_helpers

from brewpass_common.migrations import run_migrations
from catalog_service import models  # noqa: F401  (registers tables)
from catalog_service.config import get_settings
from catalog_service.db import Base

# GeoAlchemy2 helpers render spatial columns and their GiST indexes correctly.
run_migrations(
    Base.metadata,
    lambda: get_settings().database_url,
    include_object=alembic_helpers.include_object,
    process_revision_directives=alembic_helpers.writer,
    render_item=alembic_helpers.render_item,
)
