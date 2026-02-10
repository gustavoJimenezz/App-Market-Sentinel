import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base, TimestampMixin


class AppStore(enum.Enum):
    APPLE_APP_STORE = "APPLE_APP_STORE"
    GOOGLE_PLAY_STORE = "GOOGLE_PLAY_STORE"


class App(TimestampMixin, Base):
    __tablename__ = "apps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bundle_id: Mapped[str] = mapped_column(String(255), nullable=False)
    store: Mapped[AppStore] = mapped_column(
        Enum(AppStore, name="app_store_enum", create_type=False),
        nullable=False,
    )
    developer_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    icon_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    reviews: Mapped[list["Review"]] = relationship(back_populates="app")

    __table_args__ = (
        UniqueConstraint("bundle_id", "store", name="uq_apps_bundle_id_store"),
    )


class PriceHistory(Base):
    """Price history table — partitioned by RANGE on timestamp.

    PK is composite (id, timestamp) because PostgreSQL requires the
    partition key to be part of any PRIMARY KEY or UNIQUE constraint.

    No FK to apps: PostgreSQL does not propagate FK constraints from
    partitioned parent tables to child partitions. Referential integrity
    is enforced at the application layer.
    """

    __tablename__ = "price_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    region: Mapped[str] = mapped_column(String(5), nullable=False)

    __table_args__ = ({"postgresql_partition_by": "RANGE (timestamp)"},)

    __mapper_args__ = {
        "primary_key": [id, timestamp],
    }


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("apps.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_review_id: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(String(255))
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)

    app: Mapped["App"] = relationship(back_populates="reviews")

    __table_args__ = (
        UniqueConstraint(
            "app_id", "external_review_id", name="uq_reviews_app_id_external_review_id"
        ),
        Index("ix_reviews_metadata", "metadata", postgresql_using="gin"),
        Index("ix_reviews_app_id_review_date", "app_id", "review_date"),
    )
