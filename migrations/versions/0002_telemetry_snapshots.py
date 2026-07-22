"""增加每节点最新遥测快照。"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0002_telemetry_snapshots"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """兼容动态 initial metadata，只在目标表尚不存在时创建。"""

    bind = op.get_bind()
    if inspect(bind).has_table("telemetry_snapshots"):
        return
    op.create_table(
        "telemetry_snapshots",
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id"),
    )
    op.create_index(
        op.f("ix_telemetry_snapshots_observed_at"),
        "telemetry_snapshots",
        ["observed_at"],
        unique=False,
    )


def downgrade() -> None:
    """仅在表存在时删除，保证测试库可重复回退。"""

    bind = op.get_bind()
    if inspect(bind).has_table("telemetry_snapshots"):
        op.drop_table("telemetry_snapshots")
