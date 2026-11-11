"""add skill auction bidding (skill_bids, winner/price columns on skill_items)

Revision ID: b7c1d2e3f4a5
Revises: 706e7a038649
Create Date: 2026-11-11 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c1d2e3f4a5"
down_revision: str | Sequence[str] | None = "706e7a038649"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("skill_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("current_price", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(sa.Column("winner_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("final_price", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("extended_count", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.create_index(batch_op.f("ix_skill_items_winner_id"), ["winner_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_skill_items_winner_id_users", "users", ["winner_id"], ["id"]
        )

    # 기존 상품: 현재가는 시작가로. 예전 흐름(판매자가 구매자를 직접 지정)으로 이미 예약이
    # 걸린 상품은 가장 최근 예약의 구매자·금액을 낙찰 결과로 옮긴다.
    op.execute("UPDATE skill_items SET current_price = start_price")
    op.execute(
        """
        UPDATE skill_items SET
            winner_id = (
                SELECT b.buyer_id FROM skill_bookings b
                WHERE b.skill_item_id = skill_items.id
                ORDER BY b.created_at DESC, b.id DESC LIMIT 1
            ),
            final_price = (
                SELECT b.amount FROM skill_bookings b
                WHERE b.skill_item_id = skill_items.id
                ORDER BY b.created_at DESC, b.id DESC LIMIT 1
            )
        WHERE status IN ('awarded', 'closed')
        """
    )

    op.create_table(
        "skill_bids",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("skill_item_id", sa.Integer(), nullable=False),
        sa.Column("bidder_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["bidder_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["skill_item_id"], ["skill_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("skill_bids", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_skill_bids_bidder_id"), ["bidder_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_skill_bids_id"), ["id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_skill_bids_skill_item_id"), ["skill_item_id"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("skill_bids", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_skill_bids_skill_item_id"))
        batch_op.drop_index(batch_op.f("ix_skill_bids_id"))
        batch_op.drop_index(batch_op.f("ix_skill_bids_bidder_id"))
    op.drop_table("skill_bids")

    with op.batch_alter_table("skill_items", schema=None) as batch_op:
        batch_op.drop_constraint("fk_skill_items_winner_id_users", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_skill_items_winner_id"))
        batch_op.drop_column("extended_count")
        batch_op.drop_column("final_price")
        batch_op.drop_column("winner_id")
        batch_op.drop_column("current_price")
