from sqlalchemy import JSON, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.engine import Dialect


class StringArray(TypeDecorator):
    """A list-of-strings column.

    Uses native Postgres ARRAY(String) in production for efficient
    containment queries (tags.any(...)), and falls back to SQLAlchemy's
    generic JSON type on other dialects (e.g. SQLite in tests), which
    handles its own (de)serialization.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect: Dialect):
        if value is None:
            return []
        return value

    def process_result_value(self, value, dialect: Dialect):
        if value is None:
            return []
        return value
