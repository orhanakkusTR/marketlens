from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Tüm tablolar `marketlens` PostgreSQL şemasında — database-schema.md spec'i.
# İlk migration başında CREATE SCHEMA IF NOT EXISTS marketlens çalışıyor.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(schema="marketlens", naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata
