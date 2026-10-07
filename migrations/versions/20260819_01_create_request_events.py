"""Create request events table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260819_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "request_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_document_id", sa.String(length=255), nullable=False),
        sa.Column("actor_sub", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("previous_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_events_actor_sub", "request_events", ["actor_sub"])
    op.create_index("ix_request_events_event_type", "request_events", ["event_type"])
    op.create_index("ix_request_events_request_document_id", "request_events", ["request_document_id"])


def downgrade() -> None:
    op.drop_index("ix_request_events_request_document_id", table_name="request_events")
    op.drop_index("ix_request_events_event_type", table_name="request_events")
    op.drop_index("ix_request_events_actor_sub", table_name="request_events")
    op.drop_table("request_events")