"""Initial schema: apps, price_history (partitioned), reviews (JSONB)

Revision ID: 001
Revises: None
Create Date: 2026-02-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enum type ---
    app_store_enum = postgresql.ENUM(
        "APPLE_APP_STORE",
        "GOOGLE_PLAY_STORE",
        name="app_store_enum",
        create_type=False,
    )
    app_store_enum.create(op.get_bind(), checkfirst=True)

    # --- apps ---
    op.create_table(
        "apps",
        sa.Column("id", sa.UUID(), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("bundle_id", sa.String(255), nullable=False),
        sa.Column(
            "store",
            postgresql.ENUM(
                "APPLE_APP_STORE", "GOOGLE_PLAY_STORE",
                name="app_store_enum", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("developer_name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("bundle_id", "store", name="uq_apps_bundle_id_store"),
    )

    # --- price_history (partitioned) ---
    # Alembic cannot create partitioned tables natively, use raw SQL.
    op.execute("""
        CREATE TABLE price_history (
            id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            timestamp   TIMESTAMPTZ NOT NULL,
            app_id      UUID        NOT NULL,
            price       NUMERIC(10, 2) NOT NULL,
            currency    VARCHAR(3)  NOT NULL,
            region      VARCHAR(5)  NOT NULL,
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);
    """)

    # BRIN index on timestamp (efficient for append-only time-series)
    op.execute("""
        CREATE INDEX ix_price_history_timestamp_brin
        ON price_history USING BRIN (timestamp)
        WITH (pages_per_range = 32);
    """)

    # Composite B-tree index for querying by app + time range
    op.execute("""
        CREATE INDEX ix_price_history_app_id_timestamp
        ON price_history (app_id, timestamp DESC);
    """)

    # Monthly partitions: Jan 2026 → Jan 2028 (25 partitions)
    months = []
    for year in (2026, 2027):
        for month in range(1, 13):
            months.append((year, month))
    months.append((2028, 1))

    for i in range(len(months) - 1):
        y_from, m_from = months[i]
        y_to, m_to = months[i + 1]
        partition_name = f"price_history_y{y_from}m{m_from:02d}"
        op.execute(f"""
            CREATE TABLE {partition_name} PARTITION OF price_history
            FOR VALUES FROM ('{y_from}-{m_from:02d}-01')
                         TO ('{y_to}-{m_to:02d}-01');
        """)

    # Default partition for out-of-range data
    op.execute("""
        CREATE TABLE price_history_default PARTITION OF price_history DEFAULT;
    """)

    # --- reviews ---
    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column(
            "app_id",
            sa.UUID(),
            sa.ForeignKey("apps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_review_id", sa.String(255), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("author_name", sa.String(255), nullable=True),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "app_id", "external_review_id", name="uq_reviews_app_id_external_review_id"
        ),
    )

    # GIN index on metadata JSONB column
    op.execute("""
        CREATE INDEX ix_reviews_metadata
        ON reviews USING GIN (metadata);
    """)

    # Composite index for querying reviews by app + date
    op.create_index(
        "ix_reviews_app_id_review_date",
        "reviews",
        ["app_id", "review_date"],
    )


def downgrade() -> None:
    op.drop_table("reviews")
    op.execute("DROP TABLE IF EXISTS price_history CASCADE")
    op.drop_table("apps")
    op.execute("DROP TYPE IF EXISTS app_store_enum")
