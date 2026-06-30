from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "price_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("component", sa.String(50), nullable=False),
        sa.Column("market_segment", sa.String(50), nullable=False),
        sa.Column("price_value", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("price_unit", sa.String(30), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("data_source", sa.String(50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("is_validated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", "recorded_at"),
    )

    op.create_unique_constraint(
        "uq_price_component_source_time",
        "price_records",
        ["component", "data_source", "recorded_at"],
    )

    op.create_index("ix_price_component_time", "price_records", ["component", "recorded_at"])
    op.create_index("ix_price_source_time", "price_records", ["data_source", "recorded_at"])
    op.create_index("ix_price_component", "price_records", ["component"])
    op.create_index("ix_price_recorded_at", "price_records", ["recorded_at"])

    op.execute("""
               SELECT create_hypertable(
               'price_records',
               'recorded_at',
               chunk_time_interval => INTERVAL '7 days',
               if_not_exists => TRUE
               );
            """)
    
    op.create_table(
        "market_summaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("summary_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("component", sa.String(50), nullable=False),
        sa.Column("market_segment", sa.String(50), nullable=False),
        sa.Column("avg_price", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("min_price", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("max_price", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("price_unit", sa.String(30), nullable=False),
        sa.Column("price_change_pct", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_unique_constraint(
        "uq_summary_date_component_segment",
        "market_summaries",
        ["summary_date", "component", "market_segment"],
    )

    op.create_index("ix_summary_component_date", "market_summaries", ["component", "summary_date"])
    op.create_index("ix_summary_date", "market_summaries", ["summary_date"])
    
def downgrade() -> None:
    op.drop_index("ix_summary_date", table_name="market_summaries")
    op.drop_index("ix_summary_component_date", table_name="market_summaries")
    op.drop_constraint("uq_summary_date_component_segment", "market_summaries")
    op.drop_table("market_summaries")

    op.execute("SELECT drop_chunks('price_records', older_than => NOW() + INTERVAL '100 years');")
    op.drop_index("ix_price_recorded_at", table_name="price_records")
    op.drop_index("ix_price_component", table_name="price_records")
    op.drop_index("ix_price_source_time", table_name="price_records")
    op.drop_index("ix_price_component_time", table_name="price_records")
    op.drop_constraint("uq_price_component_source_time", "price_records")
    op.drop_table("price_records")
