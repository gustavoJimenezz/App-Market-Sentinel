"""Materialized view: price_trends for analytics

Revision ID: 002
Revises: 001
Create Date: 2026-03-05

"""

from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE MATERIALIZED VIEW price_trends AS
        SELECT
            app_id,
            currency,
            region,
            date_trunc('week', timestamp)   AS week,
            MIN(price)                      AS min_price,
            MAX(price)                      AS max_price,
            AVG(price)                      AS avg_price,
            COUNT(*)                        AS sample_count
        FROM price_history
        GROUP BY app_id, currency, region, date_trunc('week', timestamp);
    """)

    # Unique index required for REFRESH CONCURRENTLY
    op.execute("""
        CREATE UNIQUE INDEX ix_price_trends_pk
        ON price_trends (app_id, currency, region, week);
    """)

    # Index for querying by app ordered by week
    op.execute("""
        CREATE INDEX ix_price_trends_app_id_week
        ON price_trends (app_id, week DESC);
    """)


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS price_trends")
