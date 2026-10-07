"""Create conversation, message and notification outbox tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260820_02"
down_revision: str | None = "20260819_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_document_id", sa.String(length=255), nullable=False),
        sa.Column("opened_by_sub", sa.String(length=255), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_document_id"),
    )
    op.create_index("ix_conversations_opened_by_sub", "conversations", ["opened_by_sub"])
    op.create_index("ix_conversations_request_document_id", "conversations", ["request_document_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender_sub", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_sender_sub", "messages", ["sender_sub"])

    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_document_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("delivery_status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_outbox_delivery_status", "notification_outbox", ["delivery_status"])
    op.create_index("ix_notification_outbox_event_type", "notification_outbox", ["event_type"])
    op.create_index("ix_notification_outbox_recipient", "notification_outbox", ["recipient"])
    op.create_index("ix_notification_outbox_request_document_id", "notification_outbox", ["request_document_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_request_document_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_recipient", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_event_type", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_delivery_status", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_index("ix_messages_sender_sub", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_request_document_id", table_name="conversations")
    op.drop_index("ix_conversations_opened_by_sub", table_name="conversations")
    op.drop_table("conversations")